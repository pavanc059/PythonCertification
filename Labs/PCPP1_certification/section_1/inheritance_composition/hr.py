class PayrollSystem:
    def __init__(self, employees):
        self.employees = employees
   
    def calculate_payroll(self):
        for employee in self.employees:
            print(f"Calculating payroll for {employee.name} with ID {employee.id}.")
            print(f"Payroll amount: ${employee.calculate_payroll()}")

class Employee:
    def __init__(self, name, id):
        self.name = name
        self.id = id

class SalaryEmployee(Employee):
    def __init__(self, name, id, salary):
        super().__init__(name, id)
        self.salary = salary

    def calculate_payroll(self):
        return self.salary

class HourlyEmployee(Employee):
    def __init__(self, name, id, hourly_rate, hours_worked):
        super().__init__(name, id)
        self.hourly_rate = hourly_rate
        self.hours_worked = hours_worked

    def calculate_payroll(self):
        return self.hourly_rate * self.hours_worked
    
class CommissionEmployee(SalaryEmployee):
    def __init__(self, name, id, salary, commission_amount, sales_amount):
        super().__init__(name, id, salary)
        self.commission_amount = commission_amount
        self.sales_amount = sales_amount

    def calculate_payroll(self):
        salary = super().calculate_payroll()
        return salary + self.commission_amount 
    
