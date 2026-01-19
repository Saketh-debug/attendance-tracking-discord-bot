import discord
from discord.ext import commands
from db import get_section_id, get_students_in_section, mark_attendance,fetch_section_attendance,fetch_student_statistics,fetch_low_attendance
from db import fetch_sections,fetch_section_attendance_matrix
from features.excel_export import build_excel
from features.pdf_reports import generate_section_pdf,generate_student_stats_pdf
import os
from ui import MainMenuView
from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def start(ctx):
    await ctx.send(
        "What do you want to do?",
        view=MainMenuView(ctx)
    )

@bot.event
async def on_ready():
    print("Attendance Bot is online.")

@bot.command()
async def exportexcel(ctx):
    sections = fetch_sections()

    if not sections:
        await ctx.send("No sections found.")
        return

    file_name = "attendance_master.xlsx"
    file_path = os.path.join(".", file_name)

    build_excel(sections, fetch_section_attendance_matrix, file_path)

    await ctx.send(file=discord.File(file_path))
    os.remove(file_path)


@bot.command()
async def lowattendance(ctx, threshold: int):
    rows = fetch_low_attendance(threshold)

    if not rows:
        await ctx.send(f"No students below {threshold}% attendance.")
        return

    lines = [f"Students below **{threshold}%** attendance:\n"]

    mentions = []

    for name, username, section, total, attended in rows:
        percent = (attended / total * 100) if total else 0
        lines.append(f"- {name} ({section}) – {percent:.2f}%  [{username}]")
        mentions.append(f"@{username}")

    message = "\n".join(lines)

    # Send list
    await ctx.send(message)

    # Optional: tag them
    if mentions:
        await ctx.send(" ".join(mentions))




@bot.command()
async def studentstats(ctx):
    rows = fetch_student_statistics()

    if not rows:
        await ctx.send("No attendance data available.")
        return

    file_name = "student_statistics.pdf"
    file_path = os.path.join(".", file_name)

    generate_student_stats_pdf(rows, file_path)

    await ctx.send(file=discord.File(file_path))
    os.remove(file_path)

@bot.command()
async def sectionpdf(ctx):
    if not ctx.channel.category:
        await ctx.send("This command must be used inside a section channel.")
        return

    section_name = ctx.channel.category.name
    section_id = get_section_id(section_name)

    rows, today = fetch_section_attendance(section_id)

    if not rows:
        await ctx.send("No attendance marked for today.")
        return

    file_name = f"{section_name}_{today}.pdf"
    file_path = os.path.join(".", file_name)

    generate_section_pdf(section_name, rows, str(today), file_path)

    await ctx.send(file=discord.File(file_path))
    os.remove(file_path)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.category:
        section_name = message.channel.category.name
        section_id = get_section_id(section_name)

        if section_id:
            content = message.content.strip()

            if content.startswith("!"):
                await bot.process_commands(message)
                return
            
            # Expect: 3,7,12
            try:
                absentees = [int(x.strip()) for x in content.split(",") if x.strip()]
            except ValueError:
                await message.reply("Invalid format. Use: 3,7,12")
                return

            success, msg = mark_attendance(section_id, absentees)

            if success:
                await message.reply(
                    f"Attendance marked for **{section_name}**.\n"
                    f"Absentees: {absentees if absentees else 'None'}"
                )
            else:
                await message.reply(msg)

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
