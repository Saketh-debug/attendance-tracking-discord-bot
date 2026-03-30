import discord
from discord.ext import commands
import asyncio
import os
import logging

from db import (
    get_section_id,
    get_students_in_section,
    mark_attendance,
    fetch_section_attendance,
    fetch_student_statistics,
    fetch_low_attendance,
    fetch_sections,
    fetch_section_attendance_matrix,
    get_college_id,
    fetch_low_attendance_all,
    get_student_coordinator
)
from features.excel_export import build_excel
from features.pdf_reports import generate_section_pdf, generate_student_stats_pdf
from ui import MainMenuView, EnquireView
from config import DISCORD_TOKEN, ENV_PATH_USED


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def parse_college_from_channel(channel_name: str) -> str | None:
    if channel_name.endswith("-griet"):
        return "griet"
    if channel_name.endswith("-glec"):
        return "glec"
    return None


async def resolve_context(ctx):
    """Context resolution based on channel name."""
    if not isinstance(ctx.channel, discord.TextChannel):
        return None

    college_name = parse_college_from_channel(ctx.channel.name)
    if not college_name:
        return None

    college_id = await asyncio.to_thread(get_college_id, college_name)

    # Section resolution from Category
    section_name = None
    section_id = None
    if ctx.channel.category:
        section_name = ctx.channel.category.name
        if college_id:
            section_id = await asyncio.to_thread(get_section_id, section_name, college_id)

    return {
        "college_name": college_name,
        "college_id": college_id,
        "section_name": section_name,
        "section_id": section_id,
        "is_core_channel": ctx.channel.name.startswith("core-")
    }


@bot.command()
async def start(ctx):
    context = await resolve_context(ctx)
    if not context or not context['college_id']:
        await ctx.send("Could not identify college from this channel. Ensure channel name format ends with '-griet' or '-glec'.")
        return

    await ctx.send(
        "What do you want to do?",
        view=MainMenuView(ctx, context)
    )


@bot.event
async def on_ready():
    print("Attendance Bot is online.")


@bot.command()
async def enquire(ctx):
    username_to_check = ctx.author.name
    coord_discord_id = await asyncio.to_thread(get_student_coordinator, username_to_check)

    # Fallback if not found
    if not coord_discord_id:
        coord_discord_id = "841265152942014474"

    await ctx.send("Need help?", view=EnquireView(coord_discord_id))


@bot.command()
async def exportexcel(ctx):
    context = await resolve_context(ctx)
    if not context or not context['college_id']:
        await ctx.send("Command available only in college-specific channels.")
        return

    college_id = context['college_id']
    sections = await asyncio.to_thread(fetch_sections, college_id)

    if not sections:
        await ctx.send("No sections found for this college.")
        return

    file_name = f"attendance_master_{context['college_name']}.xlsx"
    file_path = os.path.join(".", file_name)

    await asyncio.to_thread(build_excel, sections, fetch_section_attendance_matrix, file_path)

    await ctx.send(file=discord.File(file_path))
    os.remove(file_path)


@bot.command()
async def lowattendance(ctx, threshold: int):
    context = await resolve_context(ctx)
    if not context:
        return

    if context['section_id']:
        rows = await asyncio.to_thread(fetch_low_attendance, threshold, context['section_id'])
    elif context['college_id']:
        rows = await asyncio.to_thread(fetch_low_attendance_all, threshold, context['college_id'])
    else:
        await ctx.send("Context unclear.")
        return

    if not rows:
        await ctx.send(f"No students below {threshold}% attendance.")
        return

    lines = [f"Students below **{threshold}%** attendance:\n"]
    for name, username, section, total, attended in rows:
        percent = (attended / total * 100) if total else 0
        lines.append(f"- {name} ({section}) – {percent:.2f}%  [{username}]")

    message = "\n".join(lines)
    if len(message) > 2000:
        await ctx.send(message[:2000])
        await ctx.send(message[2000:])
    else:
        await ctx.send(message)


@bot.command()
async def studentstats(ctx):
    context = await resolve_context(ctx)
    if not context:
        return

    rows = await asyncio.to_thread(
        fetch_student_statistics, context['college_id'], context['section_id']
    )

    if not rows:
        await ctx.send("No attendance data available.")
        return

    file_name = "student_statistics.pdf"
    file_path = os.path.join(".", file_name)

    await asyncio.to_thread(generate_student_stats_pdf, rows, file_path)

    await ctx.send(file=discord.File(file_path))
    os.remove(file_path)


@bot.command()
async def sectionpdf(ctx):
    context = await resolve_context(ctx)
    if not context or not context['section_id']:
        await ctx.send("This command must be used inside a section channel.")
        return

    section_name = context['section_name']
    section_id = context['section_id']

    rows, today = await asyncio.to_thread(fetch_section_attendance, section_id)

    if not rows:
        await ctx.send("No attendance marked for today.")
        return

    file_name = f"{section_name}_{today}.pdf"
    file_path = os.path.join(".", file_name)

    await asyncio.to_thread(generate_section_pdf, section_name, rows, str(today), file_path)

    await ctx.send(file=discord.File(file_path))
    os.remove(file_path)


# Keyword prefix mentors must use to trigger chat-based attendance
ABSENT_KEYWORD = "absent:"


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Process commands first
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Only parse attendance when the message explicitly starts with the keyword
    # e.g. "absent: 3,7,12"  — prevents casual messages from triggering attendance
    if message.channel.category and message.content.lower().startswith(ABSENT_KEYWORD):
        college_name = parse_college_from_channel(message.channel.name)
        if college_name:
            college_id = await asyncio.to_thread(get_college_id, college_name)
            section_name = message.channel.category.name
            section_id = await asyncio.to_thread(get_section_id, section_name, college_id)

            if section_id:
                raw = message.content[len(ABSENT_KEYWORD):].strip()
                try:
                    absentees = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
                    if absentees:
                        success, msg = await asyncio.to_thread(mark_attendance, section_id, absentees)
                        if success:
                            await message.reply(
                                f"Attendance marked for **{section_name}** ({college_name.upper()}).\n"
                                f"Absentees: {absentees}"
                            )
                        else:
                            await message.reply(msg)
                    else:
                        await message.reply(
                            "No valid roll numbers found. Format: `absent: 3,7,12`"
                        )
                except ValueError:
                    pass  # Not a valid list of ints, ignore


handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')


def start_bot():
    print("Starting bot...")
    if not DISCORD_TOKEN:
        print("\n=======================================================")
        print("ERROR: Could not find DISCORD_TOKEN!")
        print(f"I am looking for your configuration file exactly here:\n -> {ENV_PATH_USED}")
        print("\nPlease check that:")
        print("1. The file exists at that exact location.")
        print("2. The file is named exactly '.env' and NOT '.env.txt'")
        print("   (Windows often hides '.txt' extensions by default. To fix this, open any folder, go to View -> Show -> File name extensions, and rename the file).")
        print("3. Inside the file, you have exactly: DISCORD_TOKEN=your_token_here")
        print("=======================================================\n")
        print("Bot execution finished.")
        return

    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
        bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)
    except KeyboardInterrupt:
        # Must come before Exception to be reachable
        print("Bot stopped by user.")
    except Exception as e:
        print(f"Error running bot: {e}")
    finally:
        print("Bot execution finished.")


def stop_bot():
    if bot.loop and bot.loop.is_running():
        asyncio.run_coroutine_threadsafe(bot.close(), bot.loop)


if __name__ == "__main__":
    start_bot()
