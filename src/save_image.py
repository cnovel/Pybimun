import logging
import shutil
import tempfile
from argparse import ArgumentParser
import wget
import os
import requests
from PIL import Image
from src.callback import Callback

BASE = "https://bibliotheques-specialisees.paris.fr/in/dz/{}_files/"


def jpg_exists(url):
    r = requests.head(url)
    return r.status_code == requests.codes.ok


def retrieve_base_url(visio_url) -> (bool, str):
    base_url = BASE
    page = requests.get(visio_url)
    if page.status_code != requests.codes.ok:
        logging.info("Page is not accessible:", page.status_code)
        return False, ""

    html = page.text
    lines = html.split("\n")
    for line in lines:
        if "og:image" in line:
            subs = line.split("\"")
            part = subs[3][60:-4]
            return True, base_url.format(part)
    logging.info("Token og:image not found")
    return False, ""


def get_lod(base_url):
    lod = 0
    while True:
        test_lod_url = "{}/{}/0_0.jpg".format(base_url, lod)
        if jpg_exists(test_lod_url):
            lod += 1
        else:
            lod -= 1
            break
    return lod


def get_max_tiling(base_url, lod):
    max_c = 0
    max_l = 0
    while True:
        test_lod_url = "{}/{}/{}_0.jpg".format(base_url, lod, max_c)
        if jpg_exists(test_lod_url):
            max_c += 1
        else:
            break
    while True:
        test_lod_url = "{}/{}/0_{}.jpg".format(base_url, lod, max_l)
        if jpg_exists(test_lod_url):
            max_l += 1
        else:
            break
    return max_c, max_l


def dl_images(base_url, lod, max_c, max_l, cb: Callback = None) -> str:
    # From 10 to 90
    p = 10.0
    step = 80. / float(max_c * max_l)
    dir_path = tempfile.mkdtemp()
    logging.info("Working in temp folder {}".format(dir_path))
    logging.info("Downloading {} images...".format(max_c*max_l))
    for col in range(0, max_c):
        for lin in range(0, max_l):
            output = os.path.join(dir_path, "{}_{}.jpg".format(col, lin))
            wget.download("{}/{}/{}_{}.jpg".format(base_url, lod, col, lin), output)
            if cb:
                p += step
                cb.progress(p)

    logging.info("All images downloaded!")
    return dir_path


def fuse_in_columns(max_c, max_l, dir_path):
    for col in range(0, max_c):
        images = [Image.open(os.path.join(dir_path, "{}_{}.jpg".format(col, lin)))
                  for lin in range(0, max_l)]
        widths, heights = zip(*(i.size for i in images))
        total_height = sum(heights)
        max_width = max(widths)

        new_img = Image.new("RGB", (max_width, total_height))
        y_offset = 0
        for im in images:
            new_img.paste(im, (0, y_offset))
            y_offset += im.size[1]
        new_img.save(os.path.join(dir_path, "col_{}.jpg".format(col)))
        for f in [os.path.join(dir_path, "{}_{}.jpg".format(col, lin))
                  for lin in range(0, max_l)]:
            os.remove(f)
    logging.info("Columns created")


def fuse_img(max_c, dest, dir_path):
    images = [Image.open(os.path.join(dir_path, "col_{}.jpg".format(c)))
              for c in range(0, max_c)]
    widths, heights = zip(*(i.size for i in images))
    max_height = max(heights)
    total_width = sum(widths)

    full_img = Image.new("RGB", (total_width, max_height))
    x_off = 0
    for im in images:
        full_img.paste(im, (x_off, 0))
        x_off += im.size[0]
    full_img.save(dest)
    for f in [os.path.join(dir_path, "col_{}.jpg".format(c)) for c in range(0, max_c)]:
        os.remove(f)


def get_from_bib_paris(url, dest, cb: Callback = None):
    if cb:
        cb.progress(0)

    # Retrieve image url
    ok, base_url = retrieve_base_url(url)
    if not ok:
        return False
    logging.info("Base URL:")
    logging.info(base_url)
    if cb:
        cb.progress(2)

    # Check if LOD exists
    lod = get_lod(base_url)
    if lod < 0:
        logging.info("Can't find the image")
        return False
    logging.info("LOD is set at {}".format(lod))
    if cb:
        cb.progress(5)

    # Get tiling size
    max_c, max_l = get_max_tiling(base_url, lod)
    logging.info("LOD has {} columns and {} lines".format(max_c, max_l))
    if cb:
        cb.progress(10)

    # Download files in place
    dir_path = dl_images(base_url, lod, max_c, max_l, cb)
    if dir_path == "":
        return False

    # Fuse images
    fuse_in_columns(max_c, max_l, dir_path)
    if cb:
        cb.progress(95)

    fuse_img(max_c, dest, dir_path)
    shutil.rmtree(dir_path)
    logging.info("Removed temp directory")
    if cb:
        cb.progress(100)

    logging.info("Full image saved at {}".format(os.path.abspath(dest)))
    return True


class ImageDownloader:
    def __init__(self, url, output):
        self._url = url
        self._output = output

    def download(self, cb: Callback = None):
        return get_from_bib_paris(self._url, self._output, cb)

    def url(self, u=None):
        if u is not None:
            self._url = u
        return self._url

    def output(self, o=None):
        if o is not None:
            self._output = o
        return self._output


def main():
    parser = ArgumentParser(description='Download image from Paris Bibliothèque Spécialisée'
                                        ' website')
    parser.add_argument('-u', '--url', dest='url',
                        help='URL of the Visioneuse', required=True)
    parser.add_argument('-o', '--output', dest="out",
                        default="Full.jpg", help="Path of the output final image")
    args = parser.parse_args()
    img_dl = ImageDownloader(args.url, args.out)
    img_dl.download()


if __name__ == "__main__":
    main()
