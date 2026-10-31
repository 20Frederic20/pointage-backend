"""``TimeCalculationService`` of the business model: gathers what one work day
needs (planning, clockings, absences, anomalies, rules, period) and hands it to
the ``DailyTimeResult`` aggregate. Shared by the day and period handlers; the
handlers own the transaction and persistence."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from absences.domain.repositories import IAbsenceRepository
from adjustements.domain import Severity
from adjustements.domain.repositories import IAnomalyRepository
from identity.domain import EmployeeId
from periods.domain import PeriodId, PeriodStatus
from periods.domain.entities import Period
from periods.domain.repositories import IPeriodRepository
from planning.domain.repositories import IEmployeeScheduleRepository, ITimeProfileRepository
from punch.domain.repositories import ITimeEntryRepository

from ...domain.entities import DailyTimeResult
from ...domain.errors import (
    DailyTimeResultValidatedError,
    NoApplicableRuleVersionError,
    NoPeriodForDateError,
    PeriodNotOpenForCalculationError,
)
from ...domain.repositories import ICalculationRuleVersionRepository, IDailyTimeResultRepository
from ...domain.value_objects import DailyTimeResultId, PlannedDay


class TimeCalculationService:
    def __init__(
        self,
        *,
        daily_time_result_repository: IDailyTimeResultRepository,
        calculation_rule_version_repository: ICalculationRuleVersionRepository,
        period_repository: IPeriodRepository,
        employee_schedule_repository: IEmployeeScheduleRepository,
        time_profile_repository: ITimeProfileRepository,
        time_entry_repository: ITimeEntryRepository,
        absence_repository: IAbsenceRepository,
        anomaly_repository: IAnomalyRepository,
    ) -> None:
        self._results = daily_time_result_repository
        self._rule_versions = calculation_rule_version_repository
        self._periods = period_repository
        self._schedules = employee_schedule_repository
        self._time_profiles = time_profile_repository
        self._time_entries = time_entry_repository
        self._absences = absence_repository
        self._anomalies = anomaly_repository

    async def calculate_day(
        self, employee_id: EmployeeId, work_date: date, *, period: Period | None = None
    ) -> DailyTimeResult:
        """``calculerJournee``: calculate, or recalculate, one employee's work date."""
        period = period or await self._periods.find_containing(work_date)
        if period is None:
            raise NoPeriodForDateError(f"No period covers {work_date}", context=str(work_date))
        _ensure_open(period)
        rules = await self._rule_versions.find_applicable(work_date)
        if rules is None:
            raise NoApplicableRuleVersionError(
                f"No calculation rule version applies to {work_date}", context=str(work_date)
            )

        planned_day, zone = await self._planned_day(employee_id, work_date)
        day_start = datetime.combine(work_date, time.min, zone)
        day_end = datetime.combine(work_date + timedelta(days=1), time.min, zone)
        clockings = [
            (entry.occured_at, entry.entry_type)
            for entry in await self._time_entries.find_by_employee_between(employee_id, day_start, day_end)
            if entry.counts
        ]
        absences = [
            (absence.start_at, absence.end_at)
            for absence in await self._absences.find_approved_by_employee_between(employee_id, day_start, day_end)
        ]
        anomalies = await self._anomalies.find_open_by_employee_between(employee_id, day_start, day_end)
        inputs = {
            "rules": rules,
            "planned_day": planned_day,
            "clockings": clockings,
            "absences": absences,
            "has_open_blocking_anomaly": any(a.severity == Severity.BLOCKING for a in anomalies),
            "has_open_anomaly": bool(anomalies),
        }

        existing = await self._results.find_by_employee_and_date(employee_id, work_date)
        if existing is not None:
            existing.recalculate(period_id=period.id, **inputs)
            return existing
        return DailyTimeResult.calculate(
            DailyTimeResultId.generate(),
            employee_id=employee_id,
            period_id=period.id,
            work_date=work_date,
            **inputs,
        )

    async def recalculate_period(self, period_id: PeriodId) -> tuple[list[DailyTimeResult], int]:
        """``recalculerPeriode``: every day of the period for every scheduled employee.

        Returns the recalculated results and how many validated days were left untouched.
        """
        period = await self._periods.get_by_id(period_id)
        _ensure_open(period)
        # ponytail: one round of queries per employee-day; batch the reads if periods get large.
        results: list[DailyTimeResult] = []
        skipped_validated = 0
        for employee_id in await self._schedules.find_employee_ids_between(period.start_date, period.end_date):
            work_date = period.start_date
            while work_date <= period.end_date:
                try:
                    results.append(await self.calculate_day(employee_id, work_date, period=period))
                except DailyTimeResultValidatedError:
                    skipped_validated += 1
                work_date += timedelta(days=1)
        return results, skipped_validated

    async def work_date_of(self, employee_id: EmployeeId, instant: datetime) -> date:
        """The work date ``instant`` falls on, in the timezone ``calculate_day`` builds
        the employee's days in (time profile of the schedule; UTC when unscheduled).

        The schedule is looked up on the UTC date of the instant."""
        _, _, zone = await self._schedule_and_profile(employee_id, instant.astimezone(UTC).date())
        return instant.astimezone(zone).date()

    async def _schedule_and_profile(self, employee_id: EmployeeId, work_date: date):
        """The schedule applicable on ``work_date``, its time profile, and the day's timezone."""
        schedule = await self._schedules.find_applicable(employee_id, work_date)
        if schedule is None:
            return None, None, ZoneInfo("UTC")
        time_profile = await self._time_profiles.find_by_version_id(schedule.time_profile_version_id)
        if time_profile is None:
            return schedule, None, ZoneInfo("UTC")
        return schedule, time_profile, ZoneInfo(time_profile.timezone)

    async def _planned_day(self, employee_id: EmployeeId, work_date: date) -> tuple[PlannedDay | None, ZoneInfo]:
        """The planned hours from the employee's schedule, and the timezone of the day."""
        schedule, time_profile, zone = await self._schedule_and_profile(employee_id, work_date)
        if time_profile is None:
            return None, zone
        profile_version = time_profile.find_version(schedule.time_profile_version_id)
        profile_day = profile_version.day_for(work_date) if profile_version is not None else None
        if profile_day is None:
            return None, zone
        return (
            PlannedDay(
                start=datetime.combine(work_date, profile_day.start_time, zone),
                end=datetime.combine(work_date, profile_day.end_time, zone),
                planned_duration=profile_day.planned_duration(),
                tolerance=profile_day.tolerance,
            ),
            zone,
        )


def _ensure_open(period: Period) -> None:
    if period.status != PeriodStatus.OPEN:
        raise PeriodNotOpenForCalculationError(
            f"Period {period.start_date} - {period.end_date} is {period.status}", context=period.id.value
        )
