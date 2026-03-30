import discord
import asyncio
import os
from db import get_section_id, get_students_in_section
from db import mark_attendance, fetch_low_attendance, fetch_low_attendance_all
from db import fetch_section_attendance, fetch_student_statistics
from features.pdf_reports import generate_section_pdf, generate_student_stats_pdf
from features.excel_export import build_excel
from db import fetch_sections, fetch_section_attendance_matrix


def _resolve_college(channel_name: str):
    """Return college_name string from channel name suffix, or None."""
    if channel_name.endswith("-griet"):
        return "griet"
    if channel_name.endswith("-glec"):
        return "glec"
    return None


class MainMenuView(discord.ui.View):
    def __init__(self, ctx, context):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.context = context

        # If section_id exists, we are in a Mentor Channel (Section specific)
        if self.context.get('section_id'):
            self.add_item(MarkAttendanceButton())
            self.add_item(SectionPDFButton())
            self.add_item(LowAttendanceButton())
            self.add_item(StudentStatsButton())

        # If is_core_channel, we show Core options
        if self.context.get('is_core_channel'):
            self.add_item(AllDomainStatsButton())
            self.add_item(ExportExcelButton())


class MarkAttendanceButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Mark Attendance", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            college_name = _resolve_college(interaction.channel.name)
            section = interaction.channel.category.name

            from db import get_college_id
            college_id = await asyncio.to_thread(get_college_id, college_name) if college_name else None
            section_id = await asyncio.to_thread(get_section_id, section, college_id) if college_id else None

            if not section_id:
                await interaction.followup.send("Could not resolve section context.", ephemeral=True)
                return

            students = await asyncio.to_thread(get_students_in_section, section_id)

            if not students:
                await interaction.followup.send("No students found in this section.", ephemeral=True)
                return

            # Build paginated views (max 25 per select menu)
            pages = [students[i:i + 25] for i in range(0, len(students), 25)]
            total_pages = len(pages)

            # One shared session for all pages — selections are aggregated here
            session = AttendanceSession(section_id, college_name, total_pages)

            for idx, page in enumerate(pages):
                page_label = f"Select absentees for **{section}**"
                if total_pages > 1:
                    page_label += f" (Part {idx + 1}/{total_pages})"
                page_label += ":"
                await interaction.followup.send(
                    page_label,
                    view=StudentSelectView(session, idx, page)
                )

            # Send a single Submit button after all dropdown messages
            await interaction.followup.send(
                "✅ Once you've made your selections above, click **Submit** to record attendance:",
                view=SubmitAttendanceView(session, section)
            )
        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while loading students: `{e}`", ephemeral=True
            )


class SectionPDFButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Today's Attendance", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            college_name = _resolve_college(interaction.channel.name)
            section = interaction.channel.category.name

            from db import get_college_id
            college_id = await asyncio.to_thread(get_college_id, college_name) if college_name else None
            section_id = await asyncio.to_thread(get_section_id, section, college_id) if college_id else None

            rows, today = await asyncio.to_thread(fetch_section_attendance, section_id)

            if not rows:
                await interaction.followup.send("No attendance for today.")
                return

            fname = f"{section}_{today}.pdf"
            await asyncio.to_thread(generate_section_pdf, section, rows, str(today), fname)
            await interaction.followup.send(file=discord.File(fname))
            os.remove(fname)
        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while generating the PDF: `{e}`", ephemeral=True
            )


class StudentStatsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Student Statistics", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            college_name = _resolve_college(interaction.channel.name)
            section = interaction.channel.category.name

            from db import get_college_id
            college_id = await asyncio.to_thread(get_college_id, college_name) if college_name else None
            section_id = await asyncio.to_thread(get_section_id, section, college_id) if college_id else None

            rows = await asyncio.to_thread(fetch_student_statistics, college_id, section_id)

            if not rows:
                await interaction.followup.send("No attendance data available.", ephemeral=True)
                return

            fname = "student_stats.pdf"
            await asyncio.to_thread(generate_student_stats_pdf, rows, fname)
            await interaction.followup.send(file=discord.File(fname))
            os.remove(fname)
        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while generating statistics: `{e}`", ephemeral=True
            )


class LowAttendanceButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Low Attendance", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        try:
            college_name = _resolve_college(interaction.channel.name)
            section = interaction.channel.category.name

            from db import get_college_id
            college_id = await asyncio.to_thread(get_college_id, college_name) if college_name else None
            section_id = await asyncio.to_thread(get_section_id, section, college_id) if college_id else None

            # Pass both section_id AND college_id so modal can fall back to college-wide query
            await interaction.response.send_modal(LowAttendanceModal(section_id, college_id=college_id))
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: `{e}`", ephemeral=True
            )


class AllDomainStatsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="All Domain Stats", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            college_name = _resolve_college(interaction.channel.name)

            from db import get_college_id
            college_id = await asyncio.to_thread(get_college_id, college_name) if college_name else None

            rows = await asyncio.to_thread(fetch_student_statistics, college_id, None)

            if not rows:
                await interaction.followup.send("No attendance data available.", ephemeral=True)
                return

            fname = f"all_domains_stats_{college_name}.pdf"
            await asyncio.to_thread(generate_student_stats_pdf, rows, fname)
            await interaction.followup.send(file=discord.File(fname))
            os.remove(fname)
        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while generating stats: `{e}`", ephemeral=True
            )


class ExportExcelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Export Excel", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            college_name = _resolve_college(interaction.channel.name)

            from db import get_college_id
            college_id = await asyncio.to_thread(get_college_id, college_name) if college_name else None

            sections = await asyncio.to_thread(fetch_sections, college_id)

            if not sections:
                await interaction.followup.send("No sections found for this college.", ephemeral=True)
                return

            fname = f"attendance_master_{college_name}.xlsx"
            await asyncio.to_thread(build_excel, sections, fetch_section_attendance_matrix, fname)
            await interaction.followup.send(file=discord.File(fname))
            os.remove(fname)
        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while exporting Excel: `{e}`", ephemeral=True
            )


class AttendanceSession:
    """
    Shared state object created once per 'Mark Attendance' button click.
    Each StudentSelectView page stores its selections here.
    The SubmitAttendanceButton reads all pages and calls mark_attendance once.
    """
    def __init__(self, section_id: int, college_name: str, total_pages: int):
        self.section_id = section_id
        self.college_name = college_name
        self.total_pages = total_pages
        # page_index -> list of absent serial_nos (populated when each page is submitted)
        self.selections: dict = {}
        # Guard against accidental double-submit of the final Submit button
        self.submitted = False


class StudentSelectView(discord.ui.View):
    """
    Displays up to 25 students per select menu.
    Saves selections into the shared AttendanceSession — does NOT call mark_attendance.
    The SubmitAttendanceButton is responsible for the single DB write.
    """
    def __init__(self, session: AttendanceSession, page_index: int, students):
        super().__init__(timeout=300)
        self.session = session
        self.page_index = page_index

        options = [
            discord.SelectOption(
                label=f"{sno} - {name}",
                value=str(sno)
            )
            for sno, name in students
        ]

        # Discord hard limit: max 25 options per select menu
        max_v = len(options)  # already guaranteed ≤25 by pagination in MarkAttendanceButton

        self.select = discord.ui.Select(
            placeholder="Choose absentees (select none = all present)",
            options=options,
            min_values=0,
            max_values=max_v
        )
        self.select.callback = self.on_select
        self.add_item(self.select)

    async def on_select(self, interaction: discord.Interaction):
        """Save this page's selections into the shared session."""
        await interaction.response.defer(ephemeral=True)
        absentees = [int(v) for v in self.select.values]
        self.session.selections[self.page_index] = absentees

        page_num = self.page_index + 1
        total = self.session.total_pages
        saved_pages = len(self.session.selections)

        if total > 1:
            await interaction.followup.send(
                f"📋 Part {page_num}/{total} saved. "
                f"({saved_pages}/{total} parts done — click Submit when all pages are filled.)",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "📋 Selection saved — click **Submit** to record attendance.",
                ephemeral=True
            )


class SubmitAttendanceView(discord.ui.View):
    """Holds the single Submit button shown after all dropdown pages."""
    def __init__(self, session: AttendanceSession, section_name: str):
        super().__init__(timeout=300)
        self.session = session
        self.section_name = section_name
        self.add_item(SubmitAttendanceButton(session, section_name))


class SubmitAttendanceButton(discord.ui.Button):
    def __init__(self, session: AttendanceSession, section_name: str):
        super().__init__(label="Submit Attendance", style=discord.ButtonStyle.success)
        self.session = session
        self.section_name = section_name

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            if self.session.submitted:
                await interaction.followup.send(
                    "⚠️ Attendance has already been submitted for this session.",
                    ephemeral=True
                )
                return

            # Pages with no interaction yet are treated as all-present (empty list)
            all_absentees = []
            for page_idx in range(self.session.total_pages):
                all_absentees.extend(self.session.selections.get(page_idx, []))

            self.session.submitted = True
            success, msg = await asyncio.to_thread(
                mark_attendance, self.session.section_id, all_absentees
            )

            if success:
                await interaction.followup.send(
                    f"✅ Attendance marked for **{self.section_name}**.\n"
                    f"Absentees: {all_absentees if all_absentees else 'None (all present)'}"
                )
            else:
                self.session.submitted = False  # allow retry on failure
                await interaction.followup.send(f"❌ {msg}", ephemeral=True)
        except Exception as e:
            self.session.submitted = False  # allow retry on error
            await interaction.followup.send(
                f"An error occurred while marking attendance: `{e}`", ephemeral=True
            )


class LowAttendanceModal(discord.ui.Modal, title="Low Attendance Filter"):
    threshold = discord.ui.TextInput(
        label="Enter threshold percentage",
        placeholder="e.g. 75",
        required=True
    )

    def __init__(self, section_id=None, college_id=None):
        super().__init__()
        self.section_id = section_id
        self.college_id = college_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            x = int(self.threshold.value)
        except ValueError:
            await interaction.followup.send("Please enter a valid number.", ephemeral=True)
            return

        try:
            rows = []
            if self.section_id:
                rows = await asyncio.to_thread(fetch_low_attendance, x, self.section_id)
            elif self.college_id:
                rows = await asyncio.to_thread(fetch_low_attendance_all, x, self.college_id)

            if not rows:
                await interaction.followup.send(f"No students below {x}% attendance.")
                return

            lines = [f"Students below **{x}%** attendance:\n"]
            for name, username, section, total, attended in rows:
                percent = (attended / total * 100) if total else 0
                lines.append(f"- {name} ({section}) – {percent:.2f}%  [{username}]")

            message = "\n".join(lines)
            # Split if message too long for Discord's 2000 char limit
            if len(message) > 2000:
                await interaction.followup.send(message[:2000])
                await interaction.followup.send(message[2000:])
            else:
                await interaction.followup.send(message)
        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while fetching low attendance: `{e}`", ephemeral=True
            )


class EnquireView(discord.ui.View):
    def __init__(self, coordinator_id: str):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Message your coordinator",
                url=f"https://discord.com/users/{coordinator_id}",
                style=discord.ButtonStyle.link
            )
        )
