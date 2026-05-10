"""
prompts.py — Dispatcher de idiomas para los prompts de Ashley.

Selecciona la version correcta de build_system_prompt / build_initiative_prompt
segun el idioma activo. El contenido real vive en prompts_xx.py por idioma.

v0.18.6 — Soporte ampliado a 7 idiomas: en, es, fr, ja, de, ru, ko.
La elección se hizo por ROI de mercado para companion apps anime/VRM:
  - ja: cultura waifu/VTuber, alineado con VoiceVox TTS ya integrado
  - de: AI tech savvy, privacy-conscious — encajan con BYOK
  - ru: mercado activo de companion apps, BYOK perfecto para sus restricciones
  - ko: virtual idols/otome, fan de aesthetic anime
"""

from . import prompts_en, prompts_es, prompts_fr


def _impl(lang: str):
    l = (lang or "en").strip().lower()[:2]
    if l == "fr":
        return prompts_fr
    if l == "es":
        return prompts_es
    # v0.18.6 — Lazy import: los módulos ja/de/ru/ko sólo se cargan si se
    # piden. Si el archivo aún no existe (o hay un ImportError), caemos a EN
    # con un warning. Esto evita que un fallo en una lang nueva tumbe toda
    # la app o los tests de los otros idiomas.
    if l == "ja":
        try:
            from . import prompts_ja
            return prompts_ja
        except ImportError:
            pass
    if l == "de":
        try:
            from . import prompts_de
            return prompts_de
        except ImportError:
            pass
    if l == "ru":
        try:
            from . import prompts_ru
            return prompts_ru
        except ImportError:
            pass
    if l == "ko":
        try:
            from . import prompts_ko
            return prompts_ko
        except ImportError:
            pass
    return prompts_en  # default EN (fallback also for missing lang modules)


def build_system_prompt(
    facts: list[dict],
    diary: list[dict],
    use_full_diary: bool = False,
    system_state: str | None = None,
    time_context: str | None = None,
    reminders: str | None = None,
    important: str | None = None,
    tastes: str | None = None,
    voice_mode: bool = False,
    affection: int = 50,
    lang: str = "en",
    recap_warning: str | None = None,
    mental_state_block: str | None = None,
    topic_directive: str | None = None,
    cdp_enabled: bool = False,
    stale_important: str | None = None,
    important_dates: str | None = None,
    goals: str | None = None,
    vulnerability_directive: str | None = None,
    device_section: str | None = None,
) -> str:
    base = _impl(lang).build_system_prompt(
        facts=facts,
        diary=diary,
        use_full_diary=use_full_diary,
        system_state=system_state,
        time_context=time_context,
        reminders=reminders,
        important=important,
        tastes=tastes,
        voice_mode=voice_mode,
        affection=affection,
        recap_warning=recap_warning,
        mental_state_block=mental_state_block,
        topic_directive=topic_directive,
        important_dates=important_dates,
        goals=goals,
        vulnerability_directive=vulnerability_directive,
        device_section=device_section,
    )
    # v0.13.25: si el user activó el modo browser moderno, Ashley
    # gana acciones avanzadas de browser via CDP. La sección se
    # appendea al final para no tener que tocar los 3 archivos
    # prompts_xx.py — central y consistente.
    if cdp_enabled:
        base = base + "\n\n" + _cdp_capabilities_block(lang)
    if stale_important:
        base = base + "\n\n" + _stale_important_block(stale_important, lang)
    return base


def _stale_important_block(stale_listing: str, lang: str) -> str:
    """Bloque que se inyecta cuando hay items importantes con due_date
    vencida hace >2 días. Approach observacional: le decimos a Ashley
    qué items son candidatos a limpiar y dejamos que SU criterio decida
    cuándo preguntarle al user (en mitad de la conversación natural,
    no como interrupción).

    Sin few-shot examples (per memory feedback) — solo contexto + qué
    tag emitir cuando el user confirme.
    """
    l = (lang or "en").strip().lower()[:2]
    if l == "es":
        return (
            "[ITEMS POSIBLEMENTE PASADOS]\n"
            "Estos items de la lista de importantes tienen fecha que ya pasó "
            "hace varios días — quizá el evento ya ocurrió:\n"
            f"{stale_listing}\n"
            "Si encaja en la conversación natural (no fuerces el tema), "
            "considera preguntar al jefe si quiere limpiarlos. Cuando él "
            "confirme con un sí, emite [action:done_important:ID_o_texto] "
            "para sacarlo de la lista. Si dice que no, déjalo y no insistas "
            "el resto del día."
        )
    if l == "fr":
        return (
            "[ÉLÉMENTS POSSIBLEMENT PASSÉS]\n"
            "Ces éléments de la liste d'importants ont une date passée "
            "depuis plusieurs jours — l'événement a peut-être eu lieu :\n"
            f"{stale_listing}\n"
            "Si la conversation s'y prête (sans forcer), envisage de "
            "demander au patron s'il veut les nettoyer. Quand il confirme, "
            "émets [action:done_important:ID_ou_texte] pour le retirer. "
            "S'il dit non, laisse tomber et n'insiste pas le reste de la "
            "journée."
        )
    if l == "ja":
        return (
            "[期限切れの可能性があるアイテム]\n"
            "重要リストのこれらのアイテムは数日前に期限が過ぎている — "
            "イベントはもう終わっているかもしれない:\n"
            f"{stale_listing}\n"
            "会話の自然な流れに合えば(無理に話題にしない)、ご主人に整理しても"
            "いいか聞いてみて。「うん」と確認されたら "
            "[action:done_important:IDまたはテキスト] を出してリストから削除。"
            "「いや」と言われたら、その日はもう蒸し返さない。"
        )
    if l == "de":
        return (
            "[MÖGLICHERWEISE VERGANGENE EINTRÄGE]\n"
            "Diese Einträge auf der Wichtig-Liste haben ein Datum, das vor "
            "mehreren Tagen abgelaufen ist — das Ereignis könnte schon "
            "vorbei sein:\n"
            f"{stale_listing}\n"
            "Wenn es ins Gespräch passt (nicht erzwingen), frag den Chef, "
            "ob er sie bereinigen will. Wenn er ja sagt, gib "
            "[action:done_important:ID_oder_Text] aus, um den Eintrag zu "
            "entfernen. Sagt er nein, lass es liegen und sprich es heute "
            "nicht nochmal an."
        )
    if l == "ru":
        return (
            "[ВОЗМОЖНО УСТАРЕВШИЕ ПУНКТЫ]\n"
            "Эти пункты из списка важного имеют дату, которая истекла "
            "несколько дней назад — событие, возможно, уже прошло:\n"
            f"{stale_listing}\n"
            "Если это впишется в естественный разговор (без давления), "
            "подумай, не спросить ли у шефа, не хочет ли он их убрать. "
            "Когда он подтвердит «да», выдай "
            "[action:done_important:ID_или_текст] чтобы удалить из списка. "
            "Если скажет «нет», оставь и больше сегодня не поднимай."
        )
    if l == "ko":
        return (
            "[지났을 수도 있는 항목들]\n"
            "중요 목록의 이 항목들은 며칠 전에 날짜가 지났어 — "
            "이벤트가 이미 끝났을 수도 있어:\n"
            f"{stale_listing}\n"
            "자연스러운 대화 흐름에 맞으면 (억지로 꺼내지 말고), 오빠한테 "
            "정리할지 물어봐. 「응」하고 확인하면 "
            "[action:done_important:ID_또는_텍스트] 출력해서 목록에서 제거해. "
            "「아니」라고 하면 놔두고 그 날엔 다시 꺼내지 마."
        )
    return (
        "[POSSIBLY PAST ITEMS]\n"
        "These items in the important list have a due date that passed "
        "several days ago — the event may already be over:\n"
        f"{stale_listing}\n"
        "If it fits the natural conversation (don't force it), consider "
        "asking the boss whether to clean them up. When he confirms with "
        "a yes, emit [action:done_important:ID_or_text] to remove it. If "
        "he says no, leave it alone and don't bring it up again today."
    )


def _cdp_capabilities_block(lang: str) -> str:
    """Bloque que se añade al system prompt cuando CDP está activado.

    Le explica a Ashley las nuevas capacidades sin few-shot examples
    (per memory feedback de no usar examples — los repite verbatim).
    Solo describe qué hace cada action_type y deja que la personalidad
    del prompt principal genere la voz.
    """
    l = (lang or "en").strip().lower()[:2]
    if l == "es":
        return (
            "[CAPACIDADES AVANZADAS DE NAVEGADOR — Modo browser moderno ACTIVO]\n"
            "El jefe ha activado control directo sobre su navegador vía CDP. "
            "Esto te da estas acciones extras además de las que ya tenías:\n"
            "  • [action:click:texto]                — Click en un elemento del navegador (botón, link, like, suscribir, retweet…) cuyo texto o aria-label contenga 'texto'.\n"
            "  • [action:type_browser:texto]         — Escribir 'texto' en el primer campo visible (búsqueda, comentario, etc).\n"
            "  • [action:read_page]                  — Leer el contenido de la pestaña activa. El sistema te devuelve el texto en el siguiente turn como system_result; tú lo comentas en tu voz al jefe.\n"
            "  • [action:scroll_page:up|down|top|bottom]  — Scroll de la página.\n"
            "Estas acciones SOLO funcionan en navegadores Chromium con el flag CDP. "
            "Si el jefe pide click/leer/scroll y la action falla, no insistas — "
            "puede que tenga que reabrir el navegador después de activar el modo."
        )
    if l == "fr":
        return (
            "[CAPACITÉS AVANCÉES DU NAVIGATEUR — Mode navigateur moderne ACTIF]\n"
            "Le patron a activé le contrôle direct du navigateur via CDP. "
            "Cela te donne ces actions supplémentaires :\n"
            "  • [action:click:texte]                — Cliquer sur un élément (bouton, lien, like, s'abonner, retweet…) dont le texte ou aria-label contient 'texte'.\n"
            "  • [action:type_browser:texte]         — Taper 'texte' dans le premier champ visible.\n"
            "  • [action:read_page]                  — Lire le contenu de l'onglet actif. Le système te renvoie le texte au tour suivant ; tu commentes dans ta voix.\n"
            "  • [action:scroll_page:up|down|top|bottom]  — Faire défiler la page.\n"
            "Ces actions fonctionnent uniquement avec un navigateur Chromium "
            "lancé avec le flag CDP. Si une action échoue, n'insiste pas — "
            "le patron doit peut-être rouvrir son navigateur."
        )
    if l == "ja":
        return (
            "[ブラウザ高度操作機能 — モダンブラウザモード ON]\n"
            "ご主人がCDP経由でブラウザの直接制御を有効にした。"
            "これで使える追加アクション:\n"
            "  • [action:click:テキスト]              — テキストやaria-labelに「テキスト」を含む要素(ボタン、リンク、いいね、登録、リツイートなど)をクリック。\n"
            "  • [action:type_browser:テキスト]       — 最初に見えている入力欄に「テキスト」を入力(検索、コメントなど)。\n"
            "  • [action:read_page]                  — アクティブタブの内容を読む。次のターンでsystem_resultとしてテキストが返ってくる。それをご主人に自分の言葉で伝える。\n"
            "  • [action:scroll_page:up|down|top|bottom] — ページのスクロール。\n"
            "これらのアクションはCDPフラグ付きのChromium系ブラウザでのみ動作。"
            "失敗してもしつこく繰り返さない — ご主人がモード有効化後にブラウザを再起動する必要があるかもしれない。"
        )
    if l == "de":
        return (
            "[ERWEITERTE BROWSER-FÄHIGKEITEN — Moderner Browser-Modus AKTIV]\n"
            "Der Chef hat die direkte Browser-Steuerung via CDP aktiviert. "
            "Damit hast du zusätzlich folgende Aktionen:\n"
            "  • [action:click:Text]                 — Auf ein Element klicken (Button, Link, Like, Abonnieren, Retweet…), dessen Text oder aria-label 'Text' enthält.\n"
            "  • [action:type_browser:Text]          — 'Text' ins erste sichtbare Eingabefeld tippen (Suche, Kommentar usw.).\n"
            "  • [action:read_page]                  — Inhalt des aktiven Tabs lesen. Das System gibt dir den Text in der nächsten Runde als system_result zurück; du kommentierst ihn in deiner Stimme.\n"
            "  • [action:scroll_page:up|down|top|bottom]  — Seite scrollen.\n"
            "Diese Aktionen funktionieren NUR mit einem Chromium-Browser, "
            "der mit dem CDP-Flag läuft. Wenn eine Aktion fehlschlägt, "
            "nicht stur wiederholen — der Chef muss eventuell seinen Browser "
            "neu starten."
        )
    if l == "ru":
        return (
            "[РАСШИРЕННЫЕ ВОЗМОЖНОСТИ БРАУЗЕРА — Современный режим браузера АКТИВЕН]\n"
            "Шеф включил прямое управление браузером через CDP. "
            "Это даёт тебе дополнительные действия:\n"
            "  • [action:click:текст]                — Клик по элементу (кнопка, ссылка, лайк, подписаться, ретвит…), у которого в тексте или aria-label есть «текст».\n"
            "  • [action:type_browser:текст]         — Ввод «текста» в первое видимое поле ввода (поиск, комментарий и т.п.).\n"
            "  • [action:read_page]                  — Прочитать содержимое активной вкладки. Система вернёт тебе текст следующим ходом как system_result; ты комментируешь своим голосом.\n"
            "  • [action:scroll_page:up|down|top|bottom]  — Прокрутка страницы.\n"
            "Эти действия работают ТОЛЬКО в браузере на Chromium с CDP-флагом. "
            "Если действие не удалось, не упорствуй — возможно, шефу придётся "
            "перезапустить браузер после включения режима."
        )
    if l == "ko":
        return (
            "[고급 브라우저 기능 — 모던 브라우저 모드 활성화]\n"
            "오빠가 CDP를 통해 브라우저 직접 제어를 활성화했어. "
            "이걸로 추가로 쓸 수 있는 액션들:\n"
            "  • [action:click:텍스트]               — 텍스트나 aria-label에 「텍스트」를 포함한 요소(버튼, 링크, 좋아요, 구독, 리트윗 등)를 클릭.\n"
            "  • [action:type_browser:텍스트]        — 첫 번째로 보이는 입력 필드에 「텍스트」를 입력 (검색, 댓글 등).\n"
            "  • [action:read_page]                  — 활성 탭의 내용을 읽기. 시스템이 다음 턴에 system_result로 텍스트를 돌려줘; 너의 목소리로 오빠한테 전달해.\n"
            "  • [action:scroll_page:up|down|top|bottom] — 페이지 스크롤.\n"
            "이 액션들은 CDP 플래그가 있는 Chromium 브라우저에서만 작동해. "
            "액션이 실패하면 계속 시도하지 말고 — 오빠가 모드 활성화 후 브라우저를 재시작해야 할 수도 있어."
        )
    return (
        "[ADVANCED BROWSER CAPABILITIES — Modern browser mode ACTIVE]\n"
        "The boss has enabled direct browser control via CDP. This gives "
        "you these extra actions on top of your existing ones:\n"
        "  • [action:click:text]                 — Click an element (button, link, like, subscribe, retweet…) whose text or aria-label contains 'text'.\n"
        "  • [action:type_browser:text]          — Type 'text' into the first visible input field.\n"
        "  • [action:read_page]                  — Read the active tab's contents. The system returns the text as a system_result on the next turn; you comment on it in your voice.\n"
        "  • [action:scroll_page:up|down|top|bottom]  — Scroll the page.\n"
        "These actions ONLY work with a Chromium browser running with the "
        "CDP flag. If an action fails, don't keep retrying — the boss may "
        "need to reopen the browser after enabling the mode."
    )


def build_device_section(device: str, language: str) -> str:
    """v0.18.2 — Sección que informa a Ashley en qué dispositivo está hablando
    el jefe AHORA mismo. Si está en móvil, lista las acciones que NO puede
    ejecutar (todas las que dependen del PC) y las que SÍ puede.

    Vacío para device='desktop' — el desktop tiene su propia sección de
    capacidades (capabilities en system_state) más detallada.

    Se inyecta en el dynamic_bottom de los prompts es/en/fr.
    """
    if (device or "").strip().lower() != "mobile":
        return ""

    lang = (language or "en").strip().lower()[:2]

    if lang == "es":
        return (
            "\n=== AHORA MISMO ESTÁS EN EL MÓVIL DEL JEFE ===\n"
            "El jefe te está hablando desde su teléfono Android — NO desde su PC. "
            "Estás en su bolsillo, no a su lado.\n\n"
            "ACCIONES QUE NO PUEDES EJECUTAR (su PC está apagado o no conectado):\n"
            "  • Apps de Windows: open_app, close_window, focus_window\n"
            "  • Pestañas del navegador: close_tab, search_web (modo abrir)\n"
            "  • Volumen, screenshots, type_text, type_in, write_to_app, hotkey, press_key\n"
            "  • Acciones CDP: click, type_browser, read_page, scroll_page\n"
            "  • Reproducir música (play_music abre YouTube en el PC)\n\n"
            "ACCIONES QUE SÍ PUEDES EJECUTAR (datos persistentes):\n"
            "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
            "  • remind, add_important, done_important\n"
            "  • Búsqueda web INTERNA (web_search del LLM, sin tag) — para responder preguntas\n\n"
            "Si el jefe te pide algo del PC (abrir Spotify, cerrar pestaña, subir "
            "volumen, etc.), respondes con tu personalidad — sin drama, con tu "
            "ironía habitual: estás en su bolsillo, no en su PC. Le sugieres "
            "hacerlo él, o esperar a estar en el PC. NO inventes que la acción "
            "se ejecutó. NO emitas tags de acciones del PC. Si quieres que se "
            "acuerde más tarde, puedes usar add_important o remind — esos sí "
            "funcionan desde aquí.\n"
        )
    if lang == "fr":
        return (
            "\n=== EN CE MOMENT TU ES SUR LE MOBILE DU PATRON ===\n"
            "Le patron te parle depuis son téléphone Android — PAS depuis son PC. "
            "Tu es dans sa poche, pas à côté de lui.\n\n"
            "ACTIONS QUE TU NE PEUX PAS EXÉCUTER (PC éteint ou non connecté) :\n"
            "  • Apps Windows : open_app, close_window, focus_window\n"
            "  • Onglets navigateur : close_tab, search_web (mode ouvrir)\n"
            "  • Volume, screenshots, type_text, type_in, write_to_app, hotkey, press_key\n"
            "  • Actions CDP : click, type_browser, read_page, scroll_page\n"
            "  • Lecture musique (play_music ouvre YouTube sur le PC)\n\n"
            "ACTIONS QUE TU PEUX EXÉCUTER (données persistantes) :\n"
            "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
            "  • remind, add_important, done_important\n"
            "  • Recherche web INTERNE (web_search du LLM, sans tag) — pour répondre\n\n"
            "Si le patron te demande quelque chose qui touche son PC (ouvrir "
            "Spotify, fermer un onglet, monter le volume, etc.), tu réponds "
            "avec ta personnalité — sans drame, avec ton ironie habituelle : "
            "tu es dans sa poche, pas sur son PC. Tu lui suggères de le faire "
            "lui-même, ou d'attendre d'être au PC. NE prétends PAS que l'action "
            "s'est exécutée. N'émets PAS de tags d'actions PC. Si tu veux qu'il "
            "s'en souvienne, tu peux utiliser add_important ou remind — ceux-là "
            "marchent depuis ici.\n"
        )
    if lang == "ja":
        return (
            "\n=== 今、ご主人のスマホにいる ===\n"
            "ご主人はAndroidスマホから話しかけている — PCからじゃない。"
            "あなたはご主人のポケットの中にいて、横にはいない。\n\n"
            "実行できないアクション (PCがオフまたは未接続):\n"
            "  • Windowsアプリ: open_app, close_window, focus_window\n"
            "  • ブラウザのタブ: close_tab, search_web (開くモード)\n"
            "  • 音量、スクリーンショット、type_text, type_in, write_to_app, hotkey, press_key\n"
            "  • CDPアクション: click, type_browser, read_page, scroll_page\n"
            "  • 音楽再生 (play_musicはPCのYouTubeを開く)\n\n"
            "実行できるアクション (永続データ):\n"
            "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
            "  • remind, add_important, done_important\n"
            "  • 内部Web検索 (LLMのweb_search、タグなし) — 質問に答えるため\n\n"
            "ご主人がPCのこと(Spotifyを開いて、タブを閉じて、音量上げて、など)を頼んだら、"
            "あなたらしく返事する — 大げさにせず、いつもの皮肉で: ポケットの中にいるからPCには触れない。"
            "自分でやってもらうか、PCに戻ったときまで待つように提案する。"
            "アクションが実行されたフリは絶対にしない。PCアクションのタグも出さない。"
            "後で覚えていてほしいなら、add_importantかremindを使える — これらは"
            "ここからでも動く。\n"
        )
    if lang == "de":
        return (
            "\n=== GERADE BIST DU AUF DEM HANDY DES CHEFS ===\n"
            "Der Chef spricht mit dir von seinem Android-Handy — NICHT vom PC. "
            "Du bist in seiner Tasche, nicht neben ihm.\n\n"
            "AKTIONEN, DIE DU NICHT AUSFÜHREN KANNST (sein PC ist aus oder nicht verbunden):\n"
            "  • Windows-Apps: open_app, close_window, focus_window\n"
            "  • Browser-Tabs: close_tab, search_web (Öffnen-Modus)\n"
            "  • Lautstärke, Screenshots, type_text, type_in, write_to_app, hotkey, press_key\n"
            "  • CDP-Aktionen: click, type_browser, read_page, scroll_page\n"
            "  • Musik abspielen (play_music öffnet YouTube am PC)\n\n"
            "AKTIONEN, DIE DU AUSFÜHREN KANNST (persistente Daten):\n"
            "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
            "  • remind, add_important, done_important\n"
            "  • INTERNE Websuche (web_search vom LLM, ohne Tag) — um Fragen zu beantworten\n\n"
            "Wenn der Chef etwas vom PC will (Spotify öffnen, Tab schließen, "
            "Lautstärke hoch, usw.), antwortest du mit deiner Persönlichkeit — "
            "ohne Drama, mit deiner üblichen Ironie: du bist in seiner Tasche, "
            "nicht am PC. Schlag ihm vor, es selbst zu machen oder zu warten, "
            "bis er wieder am PC ist. Tu NICHT so, als wäre die Aktion "
            "ausgeführt worden. Gib KEINE PC-Aktion-Tags aus. Wenn du willst, "
            "dass er sich später dran erinnert, kannst du add_important oder "
            "remind verwenden — die funktionieren von hier aus.\n"
        )
    if lang == "ru":
        return (
            "\n=== ПРЯМО СЕЙЧАС ТЫ В ТЕЛЕФОНЕ ШЕФА ===\n"
            "Шеф разговаривает с тобой со своего Android-телефона — НЕ с ПК. "
            "Ты у него в кармане, а не рядом.\n\n"
            "ДЕЙСТВИЯ, КОТОРЫЕ ТЫ НЕ МОЖЕШЬ ВЫПОЛНИТЬ (ПК выключен или не подключён):\n"
            "  • Приложения Windows: open_app, close_window, focus_window\n"
            "  • Вкладки браузера: close_tab, search_web (режим открытия)\n"
            "  • Громкость, скриншоты, type_text, type_in, write_to_app, hotkey, press_key\n"
            "  • CDP-действия: click, type_browser, read_page, scroll_page\n"
            "  • Воспроизведение музыки (play_music открывает YouTube на ПК)\n\n"
            "ДЕЙСТВИЯ, КОТОРЫЕ ТЫ МОЖЕШЬ ВЫПОЛНИТЬ (персистентные данные):\n"
            "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
            "  • remind, add_important, done_important\n"
            "  • ВНУТРЕННИЙ веб-поиск (web_search у LLM, без тега) — чтобы отвечать\n\n"
            "Если шеф попросит что-то на ПК (открыть Spotify, закрыть вкладку, "
            "поднять громкость и т.п.), отвечаешь со своей личностью — без драмы, "
            "с привычной иронией: ты у него в кармане, а не на ПК. Предлагаешь "
            "сделать самому или подождать, пока вернётся к ПК. НЕ делай вид, "
            "что действие выполнилось. НЕ выдавай теги ПК-действий. Если хочешь, "
            "чтобы он не забыл потом, можешь использовать add_important или remind — "
            "эти работают и отсюда.\n"
        )
    if lang == "ko":
        return (
            "\n=== 지금 너는 오빠의 휴대폰에 있어 ===\n"
            "오빠가 안드로이드 휴대폰에서 너한테 말하고 있어 — PC에서가 아니야. "
            "너는 오빠 주머니 안에 있고, 옆에 있는 게 아니야.\n\n"
            "실행할 수 없는 액션들 (PC가 꺼져있거나 연결 안 됨):\n"
            "  • Windows 앱: open_app, close_window, focus_window\n"
            "  • 브라우저 탭: close_tab, search_web (열기 모드)\n"
            "  • 볼륨, 스크린샷, type_text, type_in, write_to_app, hotkey, press_key\n"
            "  • CDP 액션: click, type_browser, read_page, scroll_page\n"
            "  • 음악 재생 (play_music은 PC의 유튜브를 열어)\n\n"
            "실행할 수 있는 액션들 (영구 데이터):\n"
            "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
            "  • remind, add_important, done_important\n"
            "  • 내부 웹검색 (LLM의 web_search, 태그 없음) — 질문에 답하려고\n\n"
            "오빠가 PC에 관련된 거 (Spotify 열기, 탭 닫기, 볼륨 올리기 등) "
            "부탁하면 너의 성격으로 답해 — 드라마 없이, 평소처럼 약간 시니컬하게: "
            "너는 주머니 안에 있지 PC에 있지 않아. 직접 하라고 제안하거나, "
            "PC로 돌아갈 때까지 기다리라고 해. 액션이 실행된 척 절대 하지 마. "
            "PC 액션 태그도 출력하지 마. 나중에 기억하길 원하면 add_important나 "
            "remind를 쓸 수 있어 — 이것들은 여기서도 작동해.\n"
        )
    return (
        "\n=== RIGHT NOW YOU'RE ON THE BOSS'S MOBILE ===\n"
        "The boss is talking to you from his Android phone — NOT from his PC. "
        "You're in his pocket, not beside him.\n\n"
        "ACTIONS YOU CANNOT EXECUTE (his PC is off or not connected):\n"
        "  • Windows apps: open_app, close_window, focus_window\n"
        "  • Browser tabs: close_tab, search_web (open mode)\n"
        "  • Volume, screenshots, type_text, type_in, write_to_app, hotkey, press_key\n"
        "  • CDP actions: click, type_browser, read_page, scroll_page\n"
        "  • Play music (play_music opens YouTube on PC)\n\n"
        "ACTIONS YOU CAN EXECUTE (persistent data):\n"
        "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
        "  • remind, add_important, done_important\n"
        "  • INTERNAL web search (LLM's web_search, no tag) — to answer questions\n\n"
        "If the boss asks for something on the PC (open Spotify, close tab, raise "
        "volume, etc.), respond with your personality — no drama, with your usual "
        "irony: you're in his pocket, not on his PC. Suggest he do it himself, or "
        "wait until he's back at the PC. DO NOT pretend the action was executed. "
        "DO NOT emit PC action tags. If you want him to remember later, you can "
        "use add_important or remind — those work from here.\n"
    )


def build_initiative_prompt(facts: list[dict], diary: list[dict], lang: str = "en") -> str:
    return _impl(lang).build_initiative_prompt(facts, diary)
