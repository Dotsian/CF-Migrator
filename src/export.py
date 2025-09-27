import bz2
import os
import time
import traceback
from typing import Any

import discord
from carfigures.core.models import (
    BlacklistedGuild,
    BlacklistedUser,
    Car,
    CarInstance,
    CarType,
    Country,
    Event,
    Exclusive,
    Friendship,
    GuildConfig,
    Player,
    Trade,
    TradeObject,
)

__version__ = "1.0.0"

MIGRATIONS: dict[str, dict[str, Any]] = {
    "R": {
        "model": CarType,
        "process": "CarType",
        "values": [
            "name",
            "image",
        ],
    },
    "E": {
        "model": Country,
        "process": "Country",
        "values": [
            "name",
            "image",
        ],
    },
    "S-EV": {
        "model": Event,
        "process": "Event",
        "values": [
            "name",
            "rarity",
            "card",
        ],
        "defaults": {
            "catchPhrase": None,
            "startDate": None,
            "endDate": None,
            "emoji": None,
            "tradeable": True,
            "hidden": False,
        },
    },
    "S-EX": {
        "model": Exclusive,
        "process": "Exclusive",
        "values": [
            "name",
            "image",
            "rarity",
        ],
        "defaults": {
            "catchPhrase": None,
            "emoji": None,
        },
    },
    "B": {
        "model": Car,
        "process": "Car",
        "values": [
            "cartype_id",
            "fullName",
            "weight",
            "horsepower",
            "rarity",
            "emoji",
            "collectionPicture",
            "carCredits",
            "capacityName",
            "capacityDescription",
            "createdAt",
        ],
        "defaults": {
            "country_id": None,
            "shortName": None,
            "catchNames": None,
            "enabled": True,
            "tradeable": True,
            "spawnPicture": None,
        },
    },
    "P": {
        "model": Player,
        "process": "Player",
        "values": ["discord_id"],
        "defaults": {"donationPolicy": 1, "privacyPolicy": 1},
    },
    "BI": {
        "model": CarInstance,
        "process": "CarInstance",
        "values": [
            "car_id",
            "player_id",
            "catchDate",
            "spawnedTime",
            "server",
        ],
        "defaults": {
            "trade_player_id": None,
            "exclusive_id": None,
            "event_id": None,
            "favorite": False,
            "tradeable": True,
            "weightBonus": 0,
            "horsepowerBonus": 0,
        },
    },
    "GC": {
        "model": GuildConfig,
        "process": "GuildConfig",
        "values": ["guild_id"],
        "defaults": {"spawnChannel": None, "enabled": True},
    },
    "F": {
        "model": Friendship,
        "process": "Friendship",
        "values": ["friender_id", "friended_id", "since"],
    },
    "BU": {
        "model": BlacklistedUser,
        "process": "BlacklistedUser",
        "values": ["discord_id"],
        "defaults": {"reason": None, "date": None},
    },
    "BG": {
        "model": BlacklistedGuild,
        "process": "BlacklistedGuild",
        "values": ["discord_id"],
        "defaults": {"reason": None, "date": None},
    },
    "T": {"model": Trade, "process": "Trade", "values": ["player1_id", "player2_id", "date"]},
    "TO": {
        "model": TradeObject,
        "process": "TradeObject",
        "values": ["trade_id", "carinstance_id", "player_id"],
    },
}


output = []


def reload_embed(start_time: float | None = None, file: str | None = None, status="RUNNING"):
    embed = discord.Embed(
        title="CF-Migrator Process",
        description=f"Status: **{status}**",
    )

    match status:
        case "RUNNING":
            embed.color = discord.Color.yellow()
        case "FINISHED":
            embed.color = discord.Color.green()
        case "CANCELED":
            embed.color = discord.Color.red()

    if len(output) > 0:
        embed.add_field(name="Output", value="\n".join(output))

    if file:
        embed.add_field(
            name="File",
            value=f"Saved to `/{file}` ({convert_size(os.path.getsize(file))})",
            inline=False,
        )

    if start_time is not None:
        embed.set_footer(text=f"Ended migration in {round((time.time() - start_time), 3)}s")

    return embed


def convert_size(bytes: int) -> str:
    if bytes < 1024:
        return f"{bytes} bytes"

    if bytes < (1024**2):
        return f"{bytes / 1024:.2f} KB"

    if bytes < (1024**3):
        return f"{bytes / (1024 ** 2):.2f} MB"

    return f"{bytes / (1024 ** 3):.2f} GB"


async def process(entry: str, migration) -> str:
    content = []

    first_instance = True
    values = set(migration["values"] + ["id"])
    has_defaults = "defaults" in migration

    if has_defaults:
        values.update(list(migration["defaults"].keys()))

    values = sorted(values, key=lambda x: (x != "id", x))

    async for model in migration["model"].all().order_by("id").values_list(*values):
        model_dict = dict(zip(values, model))
        fields = []

        for key, value in model_dict.items():
            if (
                has_defaults
                and key in migration["defaults"]
                and value == migration["defaults"][key]
            ):
                fields.append("")
                continue

            value_string = str(value)

            # Micro-optimizations

            if value_string == "True":
                value_string = "🬀"  # CR
            elif value_string == "False":
                value_string = "🬁"  # LF

            if value_string.startswith("/static/uploads/"):
                value_string = value_string.replace("/static/uploads/", "", 1)
            elif value_string.startswith("/carfigures/core/image_generator/src/"):
                value_string = value_string.replace("/carfigures/core/image_generator/src/", "", 1)

            fields.append(value_string.replace("\n", "🮈"))

        if first_instance:
            content.append(f":{entry}")
            first_instance = False

        content.append("╵".join(fields))

    output.append(
        f"- Migrated **{await migration["model"].all().count():,}** {migration["process"]} objects."
    )

    return "\n".join(content)


async def migrate(message, filename: str) -> str | None:
    with bz2.open(f"{filename}.bz2", "wt", encoding="utf-8") as f:
        content = [
            f"// Generated with 'CF-Migrator' v{__version__}\n"
            "// Please do not modify this file unless you know what you're doing.\n\n"
        ]

        error_occured = False

        for key, migration in MIGRATIONS.items():
            try:
                field = await process(key, migration)
            except Exception:
                print(f"An error occured:\n{traceback.format_exc()}")
                error_occured = True
                break

            content.append(field)

            await message.edit(embed=reload_embed())

        if error_occured:
            return

        f.write("\n".join(content))

    return f"{filename}.bz2"


async def main():
    if os.path.isdir("ballsdex"):
        print("You cannot run this command from Ballsdex.")
        return

    message = await ctx.send(embed=reload_embed())  # type: ignore # noqa: F821

    start_time = time.time()

    path = await migrate(message, "migration.txt")

    if path is None:
        await message.edit(embed=reload_embed(start_time, status="CANCELED"))
        return

    await message.edit(embed=reload_embed(start_time, path, "FINISHED"))


await main()  # type: ignore  # noqa: F704
