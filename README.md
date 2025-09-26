# CF-Migrator - v1.0.0

![CF-Migrator Thumbnail](https://raw.githubusercontent.com/Dotsian/CF-Migrator/refs/heads/main/assets/thumbnail.png)

## What is CF-Migrator

CF-Migrator is a set of utilities designed to transfer CarFigure data, that can't be loaded into Ballsdex, into a Ballsdex instance using a single file.

## Exporting data from CarFigures

You can export a new migration file by executing the following eval command on your CarFigures bot.

```py
import base64, requests

request = requests.get("https://api.github.com/repos/Dotsian/CF-Migrator/contents/src/export.py")

await ctx.invoke(
    bot.get_command("eval"),
    body=base64.b64decode(request.json()["content"]).decode()
)
```

## Importing data to Ballsdex

*TBA*
