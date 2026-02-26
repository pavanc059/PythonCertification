from hr import PayrollSystem
from productivity import ProductivitySystem
from employees import EmployeeDatabase

productivity_system = ProductivitySystem()
payroll_system = PayrollSystem()
employee_database = EmployeeDatabase()

employees = employee_database.employees()
productivity_system.track(employees, 40)
payroll_system.calculate_payroll(employees)
