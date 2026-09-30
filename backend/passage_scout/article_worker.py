import json
import sys

from .inputs import InputError, _fetch_article

if __name__ == "__main__":
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (12, 12))
        if sys.platform != "darwin":
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        print(json.dumps({"text": _fetch_article(sys.stdin.buffer.read(2049).decode())}))
    except InputError as exc:
        print(json.dumps({"error": str(exc)}))
    except Exception:
        print(json.dumps({"error": "Article could not be read safely; paste its text instead."}))
