import bz2
import os
import time
from typing import Any

from carfigures.core.models import Player, CarType, Country, Car, CarInstance, GuildConfig

__version__ = "1.0.0"

MIGRATIONS: dict[str, dict[str, Any]] = {
    "R": {
        "model": CarType,
        "process": "cartypes",
        "values": [
            "name",
            "image",
        ],
    },
    "E": {
        "model": Country,
        "process": "countries",
        "values": [
            "name",
            "image",
        ],
    },
    "B": {
        "model": Car,
        "process": "cars",
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
        "process": "car instances",
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
        "process": "players",
        "values": ["discord_id"],
        "defaults": {"donationPolicy": 1, "privacyPolicy": 1},
    },
    "GC": {
        "model": GuildConfig,
        "process": "guild configs",
        "values": ["guild_id"],
        "defaults": {"spawnChannel": None, "enabled": True},
    },
}


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

    await ctx.send(f"Migrated **{await  migration["model"].all().count():,}** {migration["process"]}")  # type: ignore  # noqa: F821

    return "\n".join(content)


async def migrate(filename: str):
    with bz2.open(f"{filename}.bz2", "wt", encoding="utf-8") as f:
        content = [
            f"- Generated with 'CF-Migrator' v{__version__}\n"
            "- Please do not modify this file unless you know what you're doing.\n\n"
        ]

        for key, migration in MIGRATIONS.items():
            content.append(await process(key, migration))

        f.write("\n".join(content))

    return f"{filename}.bz2"


async def main():
    if os.path.isdir("ballsdex"):
        print("You cannot run this command from Ballsdex.")
        return

    await ctx.send("Migrating...")  # type: ignore # noqa: F821

    t1 = time.time()

    path = await migrate("Migration.txt")

    t2 = time.time()

    await ctx.send(  # type: ignore # noqa: F821
        f"Finished migrating in `{round((t2 - t1), 3)}s`!\nFile was saved to `/{path}` ({convert_size(os.path.getsize(path))})"
    )


await main()  # type: ignore  # noqa: F704
