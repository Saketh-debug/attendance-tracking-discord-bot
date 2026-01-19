import discord
from db import get_section_id, get_students_in_section
from db import mark_attendance, fetch_low_attendance
from db import fetch_section_attendance, fetch_student_statistics
from features.pdf_reports import generate_section_pdf, generate_student_stats_pdf
from features.excel_export import build_excel
from db import fetch_sections, fetch_section_attendance_matrix
import os

class MainMenuView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=120)
        self.ctx = ctx

    @discord.ui.button(label="Mark Attendance", style=discord.ButtonStyle.primary)
    async def mark(self, interaction: discord.Interaction, button):
        section = interaction.channel.category.name
        section_id = get_section_id(section)
        students = get_students_in_section(section_id)

        # await interaction.response.send_message(
        #     f"Select absentees for **{section}**:",
        #     view=StudentSelectView(section_id, students),
        #     ephemeral=True
        # )
        await interaction.response.send_message(
            f"Select absentees for **{section}**:",
            view=StudentSelectView(section_id, students)
        )

    @discord.ui.button(label="Section PDF", style=discord.ButtonStyle.secondary)
    async def section_pdf(self, interaction, button):
        section = interaction.channel.category.name
        section_id = get_section_id(section)
        rows, today = fetch_section_attendance(section_id)

        if not rows:
            # await interaction.response.send_message("No attendance for today.", ephemeral=True)
            await interaction.response.send_message("No attendance for today.")
            return

        fname = f"{section}_{today}.pdf"
        generate_section_pdf(section, rows, str(today), fname)
        await interaction.response.send_message(file=discord.File(fname))
        os.remove(fname)

    @discord.ui.button(label="Student Stats", style=discord.ButtonStyle.secondary)
    async def stats(self, interaction, button):
        rows = fetch_student_statistics()
        fname = "student_stats.pdf"
        generate_student_stats_pdf(rows, fname)
        await interaction.response.send_message(file=discord.File(fname))
        os.remove(fname)

    @discord.ui.button(label="Low Attendance", style=discord.ButtonStyle.danger)
    async def low_attendance(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(LowAttendanceModal())

    @discord.ui.button(label="Export Excel", style=discord.ButtonStyle.success)
    async def export(self, interaction, button):
        sections = fetch_sections()
        fname = "attendance_master.xlsx"
        build_excel(sections, fetch_section_attendance_matrix, fname)
        await interaction.response.send_message(file=discord.File(fname))
        os.remove(fname)

class StudentSelectView(discord.ui.View):
    def __init__(self, section_id, students):
        super().__init__(timeout=120)
        self.section_id = section_id

        options = [
            discord.SelectOption(
                label=f"{sno} - {name}",
                value=str(sno)
            )
            for sno, name in students
        ]

        self.select = discord.ui.Select(
            placeholder="Choose absentees",
            options=options,
            min_values=0,
            max_values=len(options)
        )
        self.select.callback = self.on_submit
        self.add_item(self.select)

    async def on_submit(self, interaction: discord.Interaction):
        absentees = [int(v) for v in self.select.values]
        mark_attendance(self.section_id, absentees)

        # await interaction.response.send_message(
        #     f"Attendance marked.\nAbsentees: {absentees if absentees else 'None'}",
        #     ephemeral=True
        # )
        await interaction.response.send_message(
            f"Attendance marked.\nAbsentees: {absentees if absentees else 'None'}"
        )

class LowAttendanceModal(discord.ui.Modal, title="Low Attendance Filter"):
    threshold = discord.ui.TextInput(
        label="Enter threshold percentage",
        placeholder="e.g. 75",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            x = int(self.threshold.value)
        except ValueError:
            # await interaction.response.send_message("Please enter a valid number.", ephemeral=True)
            await interaction.response.send_message("Please enter a valid number.")
            return

        rows = fetch_low_attendance(x)

        if not rows:
            # await interaction.response.send_message(
            #     f"No students below {x}% attendance.",
            #     ephemeral=True
            # )
            await interaction.response.send_message(
                f"No students below {x}% attendance."
            )
            return

        lines = [f"Students below **{x}%** attendance:\n"]
        mentions = []

        for name, username, section, total, attended in rows:
            percent = (attended / total * 100) if total else 0
            lines.append(f"- {name} ({section}) – {percent:.2f}%  [{username}]")
            mentions.append(f"@{username}")

        await interaction.response.send_message("\n".join(lines))
        if mentions:
            await interaction.followup.send(" ".join(mentions))
