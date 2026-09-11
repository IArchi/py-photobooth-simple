import cv2
import numpy as np
from PIL import Image

from libs.template_collage import TemplateCollage
from libs.screens import OpenCvVideoPreview


def _template(tmp_path):
    template_path = tmp_path / 'media.json'
    template_path.write_text(
        '{"name":"Media","page":{"width":64,"height":48},'
        '"photos":[{"x":0,"y":0,"width":64,"height":48}],'
        '"background":null,"foreground":null}',
        encoding='utf-8',
    )
    return TemplateCollage(str(template_path))


def test_assemble_gif_uses_all_frames_and_delay(tmp_path):
    template = _template(tmp_path)
    paths = []
    for index, color in enumerate(((0, 0, 255), (0, 255, 0), (255, 0, 0))):
        path = tmp_path / f'frame-{index}.jpg'
        cv2.imwrite(str(path), np.full((48, 64, 3), color, dtype=np.uint8))
        paths.append(str(path))

    output = tmp_path / 'result.gif'
    template.assemble_gif(paths, str(output), 0.25)

    gif = Image.open(output)
    assert gif.n_frames == 3
    assert gif.info['duration'] == 250


def test_record_video_writes_silent_frames(tmp_path):
    template = _template(tmp_path)
    output = tmp_path / 'result.mp4'
    frame = np.full((48, 64, 3), 127, dtype=np.uint8)

    template.record_video(lambda _ratio: frame, str(output), 0.12, 10)

    capture = cv2.VideoCapture(str(output))
    try:
        assert capture.isOpened()
        assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) >= 1
    finally:
        capture.release()


def test_opencv_video_preview_reads_and_loops_video(tmp_path):
    output = tmp_path / 'preview.mp4'
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*'mp4v'), 10, (64, 48))
    writer.write(np.full((48, 64, 3), 127, dtype=np.uint8))
    writer.release()

    preview = OpenCvVideoPreview()
    preview.play(str(output))
    try:
        assert preview.texture is not None
        preview._next_frame(0)
        assert preview.texture is not None
    finally:
        preview.stop()
