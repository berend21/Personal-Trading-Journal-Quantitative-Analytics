from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
import os

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
MAX_IMAGE_WIDTH = 10000
MAX_IMAGE_HEIGHT = 10000
MAX_IMAGE_PIXELS = 25_000_000

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
MAX_IMAGE_SIZE = 20 * 1024 * 1024

def get_safe_extension(filename):
    filename = secure_filename(filename or '')

    if not filename:
        return None

    _, extension = os.path.splitext(filename)
    extension = extension.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return None

    return extension


def validate_image(file, expected_extension):
    try:
        image = Image.open(file)

        image.verify()

        file.seek(0)

        image = Image.open(file)

        width, height = image.size

        if width > MAX_IMAGE_WIDTH:
            return False

        if height > MAX_IMAGE_HEIGHT:
            return False

        if width * height > MAX_IMAGE_PIXELS:
            return False

        expected_formats = {
            '.jpg': {'JPEG'},
            '.jpeg': {'JPEG'},
            '.png': {'PNG'},
            '.webp': {'WEBP'},
        }

        allowed_formats = expected_formats.get(
            expected_extension,
            set()
        )

        if image.format not in allowed_formats:
            return False

        file.seek(0)

        return True

    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        ValueError,
    ):
        file.seek(0)
        return False

