from __future__ import annotations

import base64
import hashlib
import http.server as _BaseHTTPServer
import logging
import os
import re
import threading
import time
import typing
import urllib.parse as _urlparse
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus as _StatusCodes
from queue import Queue
from urllib.parse import urlencode as _urlencode

import click
import requests

from .default_html import get_default_success_html
from .exceptions import AccessTokenNotFoundError
from .keyring import Credentials

_code_verifier_length = 64
_random_seed_length = 40
_utf_8 = "utf-8"


def _generate_code_verifier():
    """
    Generates a 'code_verifier' as described in https://tools.ietf.org/html/rfc7636#section-4.1
    Adapted from https://github.com/openstack/deb-python-oauth2client/blob/master/oauth2client/_pkce.py.
    :return str:
    """
    code_verifier = base64.urlsafe_b64encode(os.urandom(_code_verifier_length)).decode(_utf_8)
    # Eliminate invalid characters.
    code_verifier = re.sub(r"[^a-zA-Z0-9_\-.~]+", "", code_verifier)
    if len(code_verifier) < 43:
        raise ValueError("Verifier too short. number of bytes must be > 30.")
    elif len(code_verifier) > 128:
        raise ValueError("Verifier too long. number of bytes must be < 97.")
    return code_verifier


def _generate_state_parameter():
    state = base64.urlsafe_b64encode(os.urandom(_random_seed_length)).decode(_utf_8)
    # Eliminate invalid characters.
    code_verifier = re.sub("[^a-zA-Z0-9-_.,]+", "", state)
    return code_verifier


def _create_code_challenge(code_verifier):
    """
    Adapted from https://github.com/openstack/deb-python-oauth2client/blob/master/oauth2client/_pkce.py.
    :param str code_verifier: represents a code verifier generated by generate_code_verifier()
    :return str: urlsafe base64-encoded sha256 hash digest
    """
    code_challenge = hashlib.sha256(code_verifier.encode(_utf_8)).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode(_utf_8)
    # Eliminate invalid characters
    code_challenge = code_challenge.replace("=", "")
    return code_challenge


class AuthorizationCode(object):
    def __init__(self, code, state):
        self._code = code
        self._state = state

    @property
    def code(self):
        return self._code

    @property
    def state(self):
        return self._state


@dataclass
class EndpointMetadata(object):
    """
    This class can be used to control the rendering of the page on login successful or failure
    """

    endpoint: str
    success_html: typing.Optional[bytes] = None
    failure_html: typing.Optional[bytes] = None


class OAuthCallbackHandler(_BaseHTTPServer.BaseHTTPRequestHandler):
    """
    A simple wrapper around BaseHTTPServer.BaseHTTPRequestHandler that handles a callback URL that accepts an
    authorization token.
    """

    def do_GET(self):
        url = _urlparse.urlparse(self.path)
        if url.path.strip("/") == self.server.redirect_path.strip("/"):
            self.send_response(_StatusCodes.OK)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.handle_login(dict(_urlparse.parse_qsl(url.query)))
            if self.server.remote_metadata.success_html is None:
                self.wfile.write(bytes(get_default_success_html(self.server.remote_metadata.endpoint), "utf-8"))
            self.wfile.flush()
        else:
            self.send_response(_StatusCodes.NOT_FOUND)

    def handle_login(self, data: dict):
        self.server.handle_authorization_code(AuthorizationCode(data["code"], data["state"]))


class OAuthHTTPServer(_BaseHTTPServer.HTTPServer):
    """
    A simple wrapper around the BaseHTTPServer.HTTPServer implementation that binds an authorization_client for handling
    authorization code callbacks.
    """

    def __init__(
        self,
        server_address: typing.Tuple[str, int],
        remote_metadata: EndpointMetadata,
        request_handler_class: typing.Type[_BaseHTTPServer.BaseHTTPRequestHandler],
        bind_and_activate: bool = True,
        redirect_path: str = None,
        queue: Queue = None,
    ):
        _BaseHTTPServer.HTTPServer.__init__(self, server_address, request_handler_class, bind_and_activate)
        self._redirect_path = redirect_path
        self._remote_metadata = remote_metadata
        self._auth_code = None
        self._queue = queue

    @property
    def redirect_path(self) -> str:
        return self._redirect_path

    @property
    def remote_metadata(self) -> EndpointMetadata:
        return self._remote_metadata

    def handle_authorization_code(self, auth_code: str):
        self._queue.put(auth_code)

    def handle_request(self, queue: Queue = None) -> typing.Any:
        self._queue = queue
        return super().handle_request()


class _SingletonPerEndpoint(type):
    """
    A metaclass to create per endpoint singletons for AuthorizationClient objects
    """

    _instances: typing.Dict[str, AuthorizationClient] = {}

    def __call__(cls, *args, **kwargs):
        endpoint = ""
        if args:
            endpoint = args[0]
        elif "auth_endpoint" in kwargs:
            endpoint = kwargs["auth_endpoint"]
        else:
            raise ValueError("parameter auth_endpoint is required")
        if endpoint not in cls._instances:
            cls._instances[endpoint] = super(_SingletonPerEndpoint, cls).__call__(*args, **kwargs)
        return cls._instances[endpoint]


class AuthorizationClient(metaclass=_SingletonPerEndpoint):
    """
    Authorization client that stores the credentials in keyring and uses oauth2 standard flow to retrieve the
    credentials. NOTE: This will open an web browser to retrieve the credentials.
    """

    def __init__(
        self,
        endpoint: str,
        auth_endpoint: str,
        token_endpoint: str,
        audience: typing.Optional[str] = None,
        scopes: typing.Optional[typing.List[str]] = None,
        client_id: typing.Optional[str] = None,
        redirect_uri: typing.Optional[str] = None,
        endpoint_metadata: typing.Optional[EndpointMetadata] = None,
        verify: typing.Optional[typing.Union[bool, str]] = None,
        session: typing.Optional[requests.Session] = None,
        request_auth_code_params: typing.Optional[typing.Dict[str, str]] = None,
        request_access_token_params: typing.Optional[typing.Dict[str, str]] = None,
        refresh_access_token_params: typing.Optional[typing.Dict[str, str]] = None,
        add_request_auth_code_params_to_request_access_token_params: typing.Optional[bool] = False,
    ):
        """
        Create new AuthorizationClient

        :param endpoint: str endpoint to connect to
        :param auth_endpoint: str endpoint where auth metadata can be found
        :param token_endpoint: str endpoint to retrieve token from
        :param audience: (optional) Audience parameter for Auth0
        :param scopes: list[str] oauth2 scopes
        :param client_id: oauth2 client id
        :param redirect_uri: oauth2 redirect uri
        :param endpoint_metadata: EndpointMetadata object to control the rendering of the page on login successful or failure
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
        :param session: (optional) A custom requests.Session object to use for making HTTP requests.
            If not provided, a new Session object will be created.
        :param request_auth_code_params: (optional) dict of parameters to add to login uri opened in the browser
        :param request_access_token_params: (optional) dict of parameters to add when exchanging the auth code for the access token
        :param refresh_access_token_params: (optional) dict of parameters to add when refreshing the access token
        :param add_request_auth_code_params_to_request_access_token_params: Whether to add the `request_auth_code_params` to
            the parameters sent when exchanging the auth code for the access token. Defaults to False.
            Required e.g. for the PKCE flow with flyteadmin.
            Not required for e.g. the standard OAuth2 flow on GCP.
        """
        self._endpoint = endpoint
        self._auth_endpoint = auth_endpoint
        if endpoint_metadata is None:
            remote_url = _urlparse.urlparse(self._auth_endpoint)
            self._remote = EndpointMetadata(endpoint=remote_url.hostname)
        else:
            self._remote = endpoint_metadata
        self._token_endpoint = token_endpoint
        self._client_id = client_id
        self._audience = audience
        self._scopes = scopes or []
        self._redirect_uri = redirect_uri
        state = _generate_state_parameter()
        self._state = state
        self._verify = verify
        self._headers = {"content-type": "application/x-www-form-urlencoded"}
        self._session = session or requests.Session()
        self._lock = threading.Lock()
        self._cached_credentials = None
        self._cached_credentials_ts = None

        self._request_auth_code_params = {
            "client_id": client_id,  # This must match the Client ID of the OAuth application.
            "response_type": "code",  # Indicates the authorization code grant
            "scope": " ".join(s.strip("' ") for s in self._scopes).strip(
                "[]'"
            ),  # ensures that the /token endpoint returns an ID and refresh token
            # callback location where the user-agent will be directed to.
            "redirect_uri": self._redirect_uri,
            "state": state,
        }

        # Conditionally add audience param if provided - value is not None
        if self._audience:
            self._request_auth_code_params["audience"] = self._audience

        if request_auth_code_params:
            # Allow adding additional parameters to the request_auth_code_params
            self._request_auth_code_params.update(request_auth_code_params)

        self._request_access_token_params = request_access_token_params or {}
        self._refresh_access_token_params = refresh_access_token_params or {}

        if add_request_auth_code_params_to_request_access_token_params:
            self._request_access_token_params.update(self._request_auth_code_params)

    def __repr__(self):
        return f"AuthorizationClient({self._auth_endpoint}, {self._token_endpoint}, {self._client_id}, {self._scopes}, {self._redirect_uri})"

    def _create_callback_server(self):
        server_url = _urlparse.urlparse(self._redirect_uri)
        server_address = (server_url.hostname, server_url.port)
        return OAuthHTTPServer(
            server_address,
            self._remote,
            OAuthCallbackHandler,
            redirect_path=server_url.path,
        )

    def _request_authorization_code(self):
        scheme, netloc, path, _, _, _ = _urlparse.urlparse(self._auth_endpoint)
        query = _urlencode(self._request_auth_code_params)
        endpoint = _urlparse.urlunparse((scheme, netloc, path, None, query, None))
        logging.debug(f"Requesting authorization code through {endpoint}")

        success = webbrowser.open_new_tab(endpoint)
        if not success:
            click.secho(f"Please open the following link in your browser to authenticate: {endpoint}")

    def _credentials_from_response(self, auth_token_resp) -> Credentials:
        """
        The auth_token_resp body is of the form:
        {
          "access_token": "foo",
          "refresh_token": "bar",
          "token_type": "Bearer"
        }

        Can additionally contain "expires_in" and "id_token" fields.
        """
        response_body = auth_token_resp.json()
        refresh_token = None
        expires_in = None
        id_token = None
        if "access_token" not in response_body:
            raise ValueError('Expected "access_token" in response from oauth server')
        if "refresh_token" in response_body:
            refresh_token = response_body["refresh_token"]
        if "expires_in" in response_body:
            expires_in = response_body["expires_in"]
        access_token = response_body["access_token"]
        if "id_token" in response_body:
            id_token = response_body["id_token"]

        return Credentials(access_token, refresh_token, self._endpoint, expires_in=expires_in, id_token=id_token)

    def _request_access_token(self, auth_code) -> Credentials:
        if self._state != auth_code.state:
            raise ValueError(f"Unexpected state parameter [{auth_code.state}] passed")

        params = {
            "code": auth_code.code,
            "grant_type": "authorization_code",
        }

        params.update(self._request_access_token_params)

        resp = self._session.post(
            url=self._token_endpoint,
            data=params,
            headers=self._headers,
            allow_redirects=False,
            verify=self._verify,
        )
        if resp.status_code != _StatusCodes.OK:
            # TODO: handle expected (?) error cases:
            #  https://auth0.com/docs/flows/guides/device-auth/call-api-device-auth#token-responses
            raise RuntimeError(
                "Failed to request access token with response: [{}] {}".format(resp.status_code, resp.content)
            )
        return self._credentials_from_response(resp)

    def get_creds_from_remote(self) -> Credentials:
        """
        This is the entrypoint method. It will kickoff the full authentication
        flow and trigger a web-browser to retrieve credentials. Because this
        needs to open a port on localhost and may be called from a
        multithreaded context (e.g. pyflyte register), this call may block
        multiple threads and return a cached result for up to 60 seconds.
        """
        # In the absence of globally-set token values, initiate the token request flow
        with self._lock:
            # Clear cache if it's been more than 60 seconds since the last check
            cache_ttl_s = 60
            if self._cached_credentials_ts is not None and self._cached_credentials_ts + cache_ttl_s < time.monotonic():
                self._cached_credentials = None

            if self._cached_credentials is not None:
                return self._cached_credentials
            q = Queue()

            # First prepare the callback server in the background
            server = self._create_callback_server()

            self._request_authorization_code()

            server.handle_request(q)
            server.server_close()

            # Send the call to request the authorization code in the background

            # Request the access token once the auth code has been received.
            auth_code = q.get()
            self._cached_credentials = self._request_access_token(auth_code)
            self._cached_credentials_ts = time.monotonic()
            return self._cached_credentials

    def refresh_access_token(self, credentials: Credentials) -> Credentials:
        if credentials.refresh_token is None:
            raise AccessTokenNotFoundError("no refresh token available with which to refresh authorization credentials")

        data = {
            "refresh_token": credentials.refresh_token,
            "grant_type": "refresh_token",
            "client_id": self._client_id,
        }

        data.update(self._refresh_access_token_params)

        resp = self._session.post(
            url=self._token_endpoint,
            data=data,
            headers=self._headers,
            allow_redirects=False,
            verify=self._verify,
        )
        if resp.status_code != _StatusCodes.OK:
            # In the absence of a successful response, assume the refresh token is expired. This should indicate
            # to the caller that the AuthorizationClient is defunct and a new one needs to be re-initialized.
            raise AccessTokenNotFoundError(f"Non-200 returned from refresh token endpoint {resp.status_code}")

        return self._credentials_from_response(resp)
