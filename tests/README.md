# Tests

Offline tests for the tools. Most take the path to the tools (or the skill folder) as the first argument.

| Test | Command (from the repository root) | Note |
|---|---|---|
| data checks | `python3 -I tests/check/test_numbers.py` | |
| crops | `python3 -I tests/crop/test_contrast.py` | ImageMagick |
| places | `python3 -I tests/places/test_places.py` | |
| project update | `python3 -I tests/update/test_update.py` | |
| version check | `python3 -I tests/version/test_version.py` | starts a local test server |
| ANNO casualty lists | `python3 -I tests/anno/test_losses.py skills/genealogy/tools` | |
| book map | `python3 -I tests/book_map/test_columns.py skills/genealogy/tools` | ImageMagick |
| Porta fontium | `python3 -I tests/portafontium/test_village.py skills/genealogy/tools` | saved HTML samples |
| brake – curl | `python3 -I tests/polite/test_curl.py skills/genealogy/tools/polite.py` | |
| brake – browser images | `python3 -I tests/polite/test_browser_images.py skills/genealogy/tools` | |
| brake – Windows hook | `python3 -I tests/polite/test_hook_windows.py skills/genealogy` | |
| network guard | `python3 -I skills/genealogy/tools/polite.py tests/polite/test_net_guard.py skills/genealogy` | |
| brake | `python3 -I skills/genealogy/tools/polite.py tests/polite/test_polite.py skills/genealogy/tools/polite.py` | needs 127.0.0.2, see tests/polite/README.md |
| image cache | `python3 -I skills/genealogy/tools/polite.py tests/polite/test_cache.py skills/genealogy/tools` | part 2 needs 127.0.0.2 |
| nginx gate | `python3 -I tests/web/test_nginx.py` | |
| website verify | `python3 -I tests/web/test_verify.py` | Node.js, local server |
| Cloudflare gate | `python3 -I tests/web/test_cloudflare.py` | Node.js, local server |

Tests never contact real archives.
