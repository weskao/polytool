# polytool

Personal text, image, conversion, and vChewing command-line utilities packaged
as one Python project.

> AI account management has moved to the independent public repository
> [ai-accounts](https://github.com/weskao/ai-accounts). This project no longer
> contains or installs those commands.

## Requirements

- Python 3.10 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Optional external binaries for image and document conversion

## Install

```sh
uv tool install --from git+https://github.com/weskao/polytool.git polytool
```

For an editable checkout:

```sh
git clone https://github.com/weskao/polytool.git
cd polytool
uv sync --locked
uv tool install --editable .
```

## Commands

| Command | Purpose |
| --- | --- |
| `gtrans` | Translate text or files and copy the result to the clipboard |
| `charcount` | Count characters with an optional limit |
| `imgmin` | Compress images without modifying the originals |
| `resize-image` | Resize JPG, PNG, and WebP files with ImageMagick |
| `towebp` | Convert PNG/JPG/JPEG files to WebP |
| `html2md` | Convert HTML files to Markdown with pandoc |
| `vcadd` | Add Bopomofo entries to a vChewing user dictionary on macOS |

## Examples

### Translation

```sh
gtrans "Hello world"                  # English to Traditional Chinese
gtrans -s zh-TW -t en "你好"
gtrans -f notes.txt -t ja
gtrans -f notes.txt -w                # overwrite the source file
```

Text longer than 4,500 characters is split at line boundaries. Clipboard output
uses `pbcopy` on macOS, the Win32 clipboard on Windows, and `wl-copy`, `xclip`,
or `xsel` on Linux.

### Character counts

```sh
charcount "Hello world"
charcount -f notes.txt
charcount -l 3000 "some text"
```

### Image compression

```sh
imgmin photo.jpg
imgmin logo.png --to-png
imgmin assets/ -r
imgmin assets/ 1                    # convert all supported files to JPEG
```

Outputs go to a sibling `imgmin-out/` directory. Originals are never modified.
The format-aware mode uses available tools such as `pngquant`, `oxipng`,
`jpegoptim`, `cwebp`, `svgo`, `gifsicle`, `sharp`, and macOS `sips`.

### Resize and convert

```sh
resize-image 100 100 avatar.png
resize-image -r 1280 720
resize-image -f 100 200 portrait.jpg

towebp
towebp -c -q 85

html2md "API Reference.html"
html2md
```

`resize-image` requires ImageMagick, `towebp` requires `cwebp`, and `html2md`
requires pandoc. On macOS the command offers to install a missing supported tool
with Homebrew; other platforms print the matching installation hint.

### vChewing

```sh
vcadd 蛋白質
vcadd 人工智慧 機器學習
```

`vcadd` is macOS-only. It appends Bopomofo readings to vChewing's
`userdata-cht.txt`; when that file belongs to a Git repository, it commits,
rebases, resolves append-only conflicts, and pushes the update.

## Development

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv build
```

## License

[MIT](LICENSE)
