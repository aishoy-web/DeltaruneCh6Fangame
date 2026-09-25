Dialogue architecture migration
===============================

Replace the matching project files with the files in this folder and add:

- dialogue_writer.py
- dialogue_portrait.py
- dialogue_content.py

eng.json is no longer required at runtime by game.py. Its current content was
migrated losslessly into dialogue_content.py so existing text IDs still work.

New dialogue authoring example:

    from dialogue import (
        DialogueScript, Message, Face, TextType, Text, Pause, Wait
    )

    bedroom_test = DialogueScript(
        "bedroom_test",
        [
            Message(
                Face("susie", 2),
                TextType("susie"),
                Text("* Hey, Kris."),
                Pause(15),
                Text(" You awake?"),
                Wait(final=True),
            )
        ],
    )

Raw DELTARUNE-style strings remain supported by DialogueWriter as well.

Portrait assets
---------------
DialoguePortrait deliberately does not guess asset filenames. Register the
actual Chapter 6 portrait assets when they are ready, for example:

    game.dialogue_box.register_static_portrait(
        "susie",
        "sprites/faces/susie.png",
    )

For animated/expression-specific portraits, register a PortraitDefinition with
loader(expression) and optional mouth_loader(expression, mouth_open).

The writer reserves the 58-pixel portrait text column whenever a face is active
even if a portrait image has not yet been registered.
