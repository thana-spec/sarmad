import os
import sys
from PIL import Image
from multiprocessing import Pool, cpu_count
from functools import partial
from tqdm import tqdm

MAX_SIZE_MB = 2
MAX_SIZE = MAX_SIZE_MB * 1024 * 1024  # in bytes

def compress_image(filepath, quality_start=85):
    try:
        original_size = os.path.getsize(filepath)
        if original_size <= MAX_SIZE:
            return ("skipped", filepath, original_size, original_size)

        img = Image.open(filepath)
        is_png = filepath.lower().endswith(".png")

        # PNG → JPG conversion
        if is_png:
            img = img.convert("RGB")
            output_path = filepath.rsplit(".", 1)[0] + ".jpg"
            format = "JPEG"
        else:
            output_path = filepath
            format = img.format if img.format else "JPEG"

        # Try decreasing quality levels quickly
        for q in [quality_start, 75, 60, 50, 40]:
            img.save(output_path, format, quality=q, optimize=True)
            if os.path.getsize(output_path) <= MAX_SIZE:
                return ("ok", filepath, original_size, os.path.getsize(output_path))

        # If still too large → resize once
        w, h = img.size
        ratio = (MAX_SIZE / original_size) ** 0.5
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

        img.save(output_path, format, quality=60, optimize=True)
        final_size = os.path.getsize(output_path)

        if final_size <= MAX_SIZE:
            return ("ok", filepath, original_size, final_size)
        else:
            return ("fail", filepath, original_size, final_size)

    except Exception as e:
        return ("error", filepath, 0, 0, str(e))


def find_images(directory):
    exts = (".jpg", ".jpeg", ".png")
    files = []
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            if f.lower().endswith(exts):
                files.append(os.path.join(root, f))
    return files


def main():
    folder = "SARMD/assets/images"
    if not os.path.exists(folder):
        print("Folder not found:", folder)
        sys.exit(1)

    print("Scanning images...")
    images = find_images(folder)
    print(f"Found {len(images)} images.")

    pool = Pool(cpu_count())
    worker = partial(compress_image)

    results = []
    print("\nCompressing images...\n")

    for res in tqdm(pool.imap_unordered(worker, images), total=len(images)):
        results.append(res)

    pool.close()
    pool.join()

    # Summary
    ok = [r for r in results if r[0] == "ok"]
    fail = [r for r in results if r[0] == "fail"]
    error = [r for r in results if r[0] == "error"]
    skipped = [r for r in results if r[0] == "skipped"]

    print("\n=== SUMMARY ===")
    print(f"Compressed successfully: {len(ok)}")
    print(f"Skipped (already small): {len(skipped)}")
    print(f"Failed to reach <2MB: {len(fail)}")
    print(f"Errors: {len(error)}")

    saved = sum(o - n for _, _, o, n in ok if o and n)
    print(f"\nTotal space saved: {saved/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
