import bz2
import os
import time
from typing import Any

import discord

from carfigures.core.models import Player, CarType, Country, Car, CarInstance, GuildConfig

__version__ = "1.0"

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
            "favorite": False,
            "tradeable": True,
            "weightBonus": 0,
            "horsepowerBonus": 0,
            "locked": None,
        },
    },
    "P": {
        "model": Player,
        "process": "Player",
        "values": ["discord_id"],
        "defaults": {"donationPolicy": 1, "privacyPolicy": 1},
    },
    "GC": {
        "model": GuildConfig,
        "process": "GuildConfig",
        "values": ["guild_id"],
        "defaults": {"spawnChannel": None, "enabled": True},
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
        embed.set_footer(text=f"Finished migration in {round((time.time() - start_time), 3)}s")

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
    merged_values = set(migration["values"])
    has_defaults = hasattr(migration, "defaults")

    if has_defaults:
        merged_values.update(list(migration["defaults"].keys()))

    async for model in migration["model"].all().order_by("id").values_list(*merged_values):
        model_dict = dict(zip(merged_values, model))
        fields = []

        for key, value in model_dict.items():
            fields.append(
                f"{value}"
                if not has_defaults or value != getattr(migration["defaults"], key)
                else ""
            )

        if first_instance:
            content.append(f":{entry}")
            first_instance = False

        content.append("╵".join(fields))

    output.append(
        f"- Migrated **{await migration["model"].all().count():,}** {migration["process"]} objects."
    )

    return "\n".join(content)


async def migrate(message, filename: str):
    with bz2.open(f"{filename}.bz2", "wt", encoding="utf-8") as f:
        content = [
            f"// Generated with 'CF-Migrator' v{__version__}\n"
            "// Please do not modify this file unless you know what you're doing.\n\n"
        ]

        for key, migration in MIGRATIONS.items():
            content.append(await process(key, migration))
            await message.edit(embed=reload_embed())

        f.write("\n".join(content))

    return f"{filename}.bz2"


async def main():
    if os.path.isdir("ballsdex"):
        print("You cannot run this command from Ballsdex.")
        return

    message = await ctx.send(embed=reload_embed())  # type: ignore # noqa: F821

    start_time = time.time()

    path = await migrate(message, "migration.txt")

    await message.edit(embed=reload_embed(start_time, path, "FINISHED"))


await main()  # type: ignore  # noqa: F704
