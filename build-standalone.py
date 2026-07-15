#!/usr/bin/env python3
"""
Пересобирает автономный файл-дубль отклика из ph-resume/index.html.

Зачем нужен: GitHub Pages в России открывается через раз, поэтому нужен
один HTML-файл, который работает офлайн, без интернета вообще.

Как запустить (из корня 1-2-MVP или из любого места):
    python3 ph-resume/build-standalone.py

На выходе: «Ксения Макарова — отклик.html» в корне 1-2-MVP, ~10 МБ.

Что делает: вшивает внутрь base64 картинки, видео, субтитры и квиз.
Конфигуратор не вшивается (12 МБ, ~300 файлов) — его карточка ведёт на живую
ссылку, то есть без VPN не откроется. Это осознанно.

ГРАБЛИ, из-за которых всё молча ломалось: внутри квиза есть свои теги
</script>. Если вшить его в JS-строку как есть, этот </script> закрывает
внешний скрипт раньше времени — DEMOS не создаётся, страница мертва, но
внешне выглядит нормально. Лечится экранированием "</" → "<\\/" (см. js_str).
"""

import base64
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent          # ph-resume/
OUT = ROOT.parent / "Ксения Макарова — отклик.html"
LIVE = "https://makmakarova1995.github.io/ph-resume/"


def b64(path: pathlib.Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def js_str(text: str) -> str:
    """Строка → безопасный JS-литерал. Экранируем </script>, иначе рвёт скрипт."""
    return json.dumps(text).replace("</", "<\\/")


def main() -> int:
    src = ROOT / "index.html"
    if not src.exists():
        print(f"нет файла: {src}", file=sys.stderr)
        return 1

    s = src.read_text(encoding="utf-8")

    # 1. картинки
    for img in sorted((ROOT / "img").glob("*.png")):
        s = s.replace(f'"img/{img.name}"', '"' + b64(img, "image/png") + '"')
        print(f"  вшила {img.name:16} {img.stat().st_size / 1024:6.0f} КБ")

    # 2. видео и субтитры
    mp4, vtt = ROOT / "video/vizitka.mp4", ROOT / "video/vizitka.vtt"
    if mp4.exists():
        s = s.replace('src:"video/vizitka.mp4"', "src:" + json.dumps(b64(mp4, "video/mp4")))
        print(f"  вшила видео            {mp4.stat().st_size / 1024 / 1024:6.1f} МБ")
    if vtt.exists():
        s = s.replace("tr.src='video/vizitka.vtt'", "tr.src=" + json.dumps(b64(vtt, "text/vtt")))
        print("  вшила субтитры")

    # 3. квиз внутрь через srcdoc
    quiz = ROOT / "demos/quiz-owners/index.html"
    if quiz.exists():
        s = s.replace(
            """    const f=document.createElement('iframe');
    f.src=d.src; f.loading='lazy'; f.title=d.t;
    mb.appendChild(f);""",
            """    const f=document.createElement('iframe');
    if(d.html){ f.srcdoc=d.html; } else { f.src=d.src; }
    f.loading='lazy'; f.title=d.t;
    mb.appendChild(f);""",
        )
        s = s.replace('type:"frame", src:"demos/quiz-owners/"', 'type:"frame", src:"", html:QUIZ_HTML')
        s = s.replace("const DEMOS = {", "const QUIZ_HTML = " + js_str(quiz.read_text(encoding="utf-8")) + ";\nconst DEMOS = {")
        print(f"  вшила квиз             {quiz.stat().st_size / 1024:6.0f} КБ")

    # 4. конфигуратор — только ссылкой
    s = s.replace('type:"frame", src:"demos/configurator/"', f'type:"frame", src:"{LIVE}demos/configurator/"')
    s = s.replace(
        'note:"Квиз считает комнату прямо в браузере. Ничего о человеке не собирает."',
        'note:"Открывается по ссылке: приложение на 12 МБ в один файл не уместить."',
    )

    OUT.write_text(s, encoding="utf-8")
    print(f"\n→ {OUT.name}  {OUT.stat().st_size / 1024 / 1024:.1f} МБ")

    # самопроверка: скрипт цел, всё вшито
    ok = True
    for label, cond in [
        ("квиз вшит", "const QUIZ_HTML" in s),
        ("</script> экранирован", "<\\/script>" in s),
        ("видео внутри", 'src:"data:video/mp4' in s),
        ("картинки внутри", 'data:image/png;base64' in s),
        ("не осталось ссылок на локальные файлы", '"img/' not in s and '"video/' not in s),
    ]:
        print(f"  {'✓' if cond else '✗'} {label}")
        ok &= cond
    if not ok:
        print("\nчто-то не вшилось — открой файл и проверь", file=sys.stderr)
        return 1

    print("\nПроверь глазами: открой файл двойным кликом, ткни кружок и квиз.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
