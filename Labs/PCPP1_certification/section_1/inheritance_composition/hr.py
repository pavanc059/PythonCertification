class PayrollSystem:
   
    def calculate_payroll(self, employees):
        for employee in employees:
            print(f"Calculating payroll for {employee.name} with ID {employee.employee_id}.")
            print(f"Payroll amount: ${employee.calculate_payroll()}")


# to-do: implement calculate_payroll method in Employee, Teacher, and Administrator classes to return the payroll amount based on their roles and responsibilities.
