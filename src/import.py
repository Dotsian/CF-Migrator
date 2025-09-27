import asyncio
import bz2
import os
import time
from datetime import datetime
from typing import cast

import discord
from tortoise import Tortoise
from tortoise.fields.data import DatetimeField, FloatField, IntField

from ballsdex.core.models import (
    Ball,
    BallInstance,
    BlacklistedGuild,
    BlacklistedID,
    Economy,
    Friendship,
    GuildConfig,
    Player,
    Regime,
    Special,
    Trade,
    TradeObject,
)

__version__ = "1.0.0"


SECTIONS = {
    "R": [Regime, ["background", "name", "id"]],
    "E": [Economy, ["icon", "name", "id"]],
    "S-EV": [
        Special,
        [
            "name",
            "rarity",
            "id",
            "start_date",
            "emoji",
            "background",
            "hidden",
            "tradeable",
            "end_date",
            "catch_phrase",
        ],
    ],
    "S-EX": [
        Special,
        [
            "name",
            "rarity",
            "id",
            "background",
            "emoji",
            "catch_phrase",
        ],
    ],
    "B": [
        Ball,
        [
            "capacity_description",
            "rarity",
            "country",
            "credits",
            "id",
            "short_name",
            "health",
            "tradeable",
            "created_at",
            "emoji_id",
            "catch_names",
            "collection_card",
            "enabled",
            "attack",
            "capacity_name",
            "regime_id",
            "wild_card",
            "economy_id",
        ],
    ],
    "BI": [
        BallInstance,
        [
            "server_id",
            "ball_id",
            "player_id",
            "special_id",
            "spawned_time",
            "health_bonus",
            "favorite",
            "tradeable",
            "attack_bonus",
            "trade_player_id",
            "id",
            "special_id",
            "catch_date",
        ],
    ],
    "P": [
        Player,
        [
            "donation_policy",
            "discord_id",
            "id",
            "privacy_policy",
        ],
    ],
    "GC": [
        GuildConfig,
        [
            "guild_id",
            "enabled",
            "id",
            "spawn_channel",
        ],
    ],
    "F": [
        Friendship,
        [
            "player1_id",
            "since",
            "player2_id",
            "id",
        ],
    ],
    "BU": [
        BlacklistedID,
        [
            "reason",
            "discord_id",
            "date",
            "id",
        ],
    ],
    "BG": [
        BlacklistedGuild,
        [
            "reason",
            "discord_id",
            "date",
            "id",
        ],
    ],
    "T": [
        Trade,
        [
            "player2_id",
            "date",
            "player1_id",
            "id",
        ],
    ],
    "TO": [
        TradeObject,
        [
            "player_id",
            "id",
            "trade_id",
            "ballinstance_id",
        ],
    ],
}


def read_bz2(path: str):
    with bz2.open(path, "rb") as bz2f:
        return bz2f.read().decode().split("🮈")


output = []


def reload_embed(start_time: float | None = None, status="RUNNING"):
    embed = discord.Embed(
        title="BD-Migrator Process",
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

    if start_time is not None:
        embed.set_footer(text=f"Ended migration in {round((time.time() - start_time), 3)}s")

    return embed


async def load(message):
    lines = read_bz2("migration.txt.bz2")
    section = ""
    data = {}

    for index, line in enumerate(lines, start=1):
        line = line.rstrip()

        if line.startswith("//") or line == "":
            continue

        if line.startswith(":"):
            section = line[1:]

            if section not in SECTIONS:
                raise Exception(f"Invalid section '{section}' detected on line {index}")

            continue

        if section == "":
            continue

        section_full = SECTIONS[section]

        if section_full[0] not in data:
            data[section_full[0]] = []

        model_dict = {}
        fields = section_full[0]._meta.fields_map
        attribute_index = 0

        for value, line_data in zip(section_full[1], line.split("╵")):
            attribute_index += 1

            if line_data == "":
                continue

            if value not in fields:
                raise Exception(
                    f"Uknown value '{value}' detected on line {index:,} - "
                    f"attribute {attribute_index:,} in {section_full[0].__name__} object"
                )

            if line_data == "None":
                line_data = None
            elif line_data == "🬀":
                line_data = True
            elif line_data == "🬁":
                line_data = False

            field_type = fields[value]

            if line_data is not None:
                if isinstance(field_type, IntField):
                    line_data = int(line_data)
                elif isinstance(field_type, FloatField):
                    line_data = float(line_data)
                elif isinstance(field_type, DatetimeField):
                    line_data = datetime.fromisoformat(cast(str, line_data))

            model_dict[value] = line_data

        data[section_full[0]].append(model_dict)

    start_time = time.time()

    for item, value in data.items():
        items = []

        for model in value:
            items.append(item(**model))

        await item.bulk_create(items)

        output.append(f"- Added **{len(value):,}** {item.__name__} objects.")

        await message.edit(embed=reload_embed())

    await message.edit(embed=reload_embed(start_time, "FINISHED"))


async def clear_all_data():  # I'm not responsible if any of you eval goblins run this on your dex
    models = Tortoise.apps.get("models")

    if models is None:
        return

    await TradeObject.all().delete()
    await Trade.all().delete()
    await BallInstance.all().delete()

    for model in models.values():
        await model.all().delete()


async def main():
    if os.path.isdir("carfigures"):
        print("You cannot run this command from CarFigures.")
        return

    if not os.path.isfile("migration.txt.bz2"):
        print("Could not find `migration.txt.bz2` migration file.")
        return

    try:
        await ctx.send(  # type: ignore # noqa: F821
            "**WARNING**: All existing data on this bot will be **CLEARED**.\n"
            "Type `proceed` if you wish to proceed.\n"
            "Type `cancel` if you wish to cancel."
        )

        confirm_message = await bot.wait_for(  # type: ignore # noqa: F821
            "message",
            check=lambda m: m.author == ctx.author  # type: ignore # noqa: F821
            and m.channel == ctx.channel  # type: ignore # noqa: F821
            and m.content.lower() in ["proceed", "cancel"],
            timeout=20,
        )
    except asyncio.TimeoutError:
        await ctx.send("Canceled due to response timeout.")  # type: ignore # noqa: F821
        return

    if confirm_message.content.lower() != "proceed":
        await ctx.send("Canceled due to message response.")  # type: ignore # noqa: F821
        return

    message = await ctx.send(embed=reload_embed())  # type: ignore # noqa: F821

    await clear_all_data()
    await load(message)


await main()  # type: ignore  # noqa: F704
