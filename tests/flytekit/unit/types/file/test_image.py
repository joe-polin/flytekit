from flytekit import task, workflow
import PIL.Image


@task(disable_deck=False)
def t1() -> PIL.Image.Image:
    return PIL.Image.new("L", (100, 100), "black")


@task
def t2(im: PIL.Image.Image) -> PIL.Image.Image:
    return im


@workflow
def wf():
    t2(im=t1())


def test_image_transformer():
    wf()
