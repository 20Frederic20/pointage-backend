from sqlalchemy.dialects import postgresql

from identity.domain.specifications import EmployeeEmployeeNumberIs
from identity.infrastructure.translators import EmployeesSpecificationTranslator


def test_the_sql_filter_ignores_case_on_both_sides():
    clause = EmployeesSpecificationTranslator().translate_leaf(EmployeeEmployeeNumberIs(" EMP0000003 "))
    sql = str(clause.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert sql == "lower(employees.employee_number) = 'emp0000003'"
