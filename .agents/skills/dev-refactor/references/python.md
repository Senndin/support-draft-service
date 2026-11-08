# Example: common refactorings in Python

Worked before/after pairs for the techniques that come up most often. The examples are Python, but the techniques are language-agnostic -- never carry these idioms into a codebase written in another language, and follow the project's own style guide over the shapes shown here.

Each pair preserves behavior exactly. Adapted from the catalog at <https://refactoring.guru/refactoring/catalog>.

## Extract Method

Smell: Long Method.

```python
# BEFORE
def print_owing(invoice):
    outstanding = 0.0

    print("*** Customer Owes ***")

    for order in invoice.orders:
        outstanding += order.amount

    print(f"name: {invoice.customer}")
    print(f"amount: {outstanding}")
```

```python
# AFTER
def print_owing(invoice):
    outstanding = calculate_outstanding(invoice)
    print_banner()
    print_details(invoice, outstanding)


def calculate_outstanding(invoice):
    return sum(order.amount for order in invoice.orders)


def print_banner():
    print("*** Customer Owes ***")


def print_details(invoice, outstanding):
    print(f"name: {invoice.customer}")
    print(f"amount: {outstanding}")
```

## Extract Variable

Smell: Long Method, Comments.

```python
# BEFORE
if (platform.upper().find("MAC") > -1) and (browser.upper().find("IE") > -1) \
        and was_initialized() and resize > 0:
    ...
```

```python
# AFTER
is_mac_os = "MAC" in platform.upper()
is_ie_browser = "IE" in browser.upper()
was_resized = resize > 0

if is_mac_os and is_ie_browser and was_initialized() and was_resized:
    ...
```

## Replace Temp with Query

Smell: Long Method.

```python
# BEFORE
def total(self):
    base_price = self.quantity * self.item_price
    if base_price > 1000:
        return base_price * 0.95
    return base_price * 0.98
```

```python
# AFTER
def total(self):
    if self.base_price > 1000:
        return self.base_price * 0.95
    return self.base_price * 0.98


@property
def base_price(self):
    return self.quantity * self.item_price
```

## Replace Nested Conditional with Guard Clauses

Smell: Long Method, deep nesting.

```python
# BEFORE
def payout(self):
    if self.is_dead:
        result = self.dead_amount()
    else:
        if self.is_separated:
            result = self.separated_amount()
        else:
            if self.is_retired:
                result = self.retired_amount()
            else:
                result = self.normal_payout()
    return result
```

```python
# AFTER
def payout(self):
    if self.is_dead:
        return self.dead_amount()
    if self.is_separated:
        return self.separated_amount()
    if self.is_retired:
        return self.retired_amount()
    return self.normal_payout()
```

## Decompose Conditional

Smell: Long Method, Comments.

```python
# BEFORE
if date < SUMMER_START or date > SUMMER_END:
    charge = quantity * winter_rate + winter_service_charge
else:
    charge = quantity * summer_rate
```

```python
# AFTER
if is_not_summer(date):
    charge = winter_charge(quantity)
else:
    charge = summer_charge(quantity)


def is_not_summer(date):
    return date < SUMMER_START or date > SUMMER_END


def winter_charge(quantity):
    return quantity * winter_rate + winter_service_charge


def summer_charge(quantity):
    return quantity * summer_rate
```

## Consolidate Conditional Expression

Smell: duplicated conditional fragments.

```python
# BEFORE
def disability_amount(self):
    if self.seniority < 2:
        return 0
    if self.months_disabled > 12:
        return 0
    if self.is_part_time:
        return 0
    ...
```

```python
# AFTER
def disability_amount(self):
    if self.is_not_eligible_for_disability():
        return 0
    ...


def is_not_eligible_for_disability(self):
    return self.seniority < 2 or self.months_disabled > 12 or self.is_part_time
```

## Introduce Parameter Object

Smell: Long Parameter List, Data Clumps.

```python
# BEFORE
def amount_invoiced(self, start_date, end_date): ...
def amount_received(self, start_date, end_date): ...
def amount_overdue(self, start_date, end_date): ...
```

```python
# AFTER
@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def includes(self, day: date) -> bool:
        return self.start <= day <= self.end


def amount_invoiced(self, period: DateRange): ...
def amount_received(self, period: DateRange): ...
def amount_overdue(self, period: DateRange): ...
```

## Preserve Whole Object

Smell: Long Parameter List.

```python
# BEFORE
low = days_temperature_range.low
high = days_temperature_range.high
if plan.within_range(low, high):
    ...
```

```python
# AFTER
if plan.within_range(days_temperature_range):
    ...
```

## Replace Magic Number with Symbolic Constant

Smell: Primitive Obsession.

```python
# BEFORE
def potential_energy(mass, height):
    return mass * height * 9.81
```

```python
# AFTER
GRAVITATIONAL_CONSTANT = 9.81


def potential_energy(mass, height):
    return mass * height * GRAVITATIONAL_CONSTANT
```

## Replace Data Value with Object

Smell: Primitive Obsession.

```python
# BEFORE
class Order:
    def __init__(self, customer: str):
        self.customer = customer  # just the customer's name
```

```python
# AFTER
class Customer:
    def __init__(self, name: str):
        self.name = name

    def discount_rate(self) -> float:
        ...


class Order:
    def __init__(self, customer: Customer):
        self.customer = customer
```

## Replace Conditional with Polymorphism

Smell: Switch Statements.

```python
# BEFORE
class Bird:
    def speed(self):
        if self.type == EUROPEAN:
            return self.base_speed()
        if self.type == AFRICAN:
            return self.base_speed() - self.load_factor * self.coconuts
        if self.type == NORWEGIAN_BLUE:
            return 0 if self.is_nailed else self.base_speed(self.voltage)
        raise ValueError("Unknown bird type")
```

```python
# AFTER
class Bird:
    def speed(self):
        raise NotImplementedError


class European(Bird):
    def speed(self):
        return self.base_speed()


class African(Bird):
    def speed(self):
        return self.base_speed() - self.load_factor * self.coconuts


class NorwegianBlue(Bird):
    def speed(self):
        return 0 if self.is_nailed else self.base_speed(self.voltage)
```

## Extract Class

Smell: Large Class, Data Clumps.

```python
# BEFORE
class Person:
    def __init__(self, name, office_area_code, office_number):
        self.name = name
        self.office_area_code = office_area_code
        self.office_number = office_number

    def telephone_number(self):
        return f"({self.office_area_code}) {self.office_number}"
```

```python
# AFTER
class TelephoneNumber:
    def __init__(self, area_code, number):
        self.area_code = area_code
        self.number = number

    def __str__(self):
        return f"({self.area_code}) {self.number}"


class Person:
    def __init__(self, name, telephone: TelephoneNumber):
        self.name = name
        self.telephone = telephone

    def telephone_number(self):
        return str(self.telephone)
```

## Move Method

Smell: Feature Envy.

```python
# BEFORE
class Account:
    def overdraft_charge(self):
        if self.account_type.is_premium:
            base_charge = 10
            if self.days_overdrawn > 7:
                base_charge += (self.days_overdrawn - 7) * 0.85
            return base_charge
        return self.days_overdrawn * 1.75
```

```python
# AFTER
class AccountType:
    def overdraft_charge(self, days_overdrawn):
        if self.is_premium:
            base_charge = 10
            if days_overdrawn > 7:
                base_charge += (days_overdrawn - 7) * 0.85
            return base_charge
        return days_overdrawn * 1.75


class Account:
    def overdraft_charge(self):
        return self.account_type.overdraft_charge(self.days_overdrawn)
```

## Hide Delegate

Smell: Message Chains.

```python
# BEFORE
manager = john.department.manager
```

```python
# AFTER
class Person:
    @property
    def manager(self):
        return self.department.manager


manager = john.manager
```

## Encapsulate Collection

Smell: Data Class, Inappropriate Intimacy.

```python
# BEFORE
class Course: ...


class Person:
    def __init__(self):
        self.courses: list[Course] = []


person.courses.append(course)  # anyone can mutate the list
```

```python
# AFTER
class Person:
    def __init__(self):
        self._courses: list[Course] = []

    @property
    def courses(self) -> tuple[Course, ...]:
        return tuple(self._courses)

    def add_course(self, course: Course) -> None:
        self._courses.append(course)

    def remove_course(self, course: Course) -> None:
        self._courses.remove(course)
```

## Introduce Null Object

Smell: Switch Statements, repeated `None` checks.

```python
# BEFORE
customer = site.customer
plan = BillingPlan.basic() if customer is None else customer.plan
name = "occupant" if customer is None else customer.name
```

```python
# AFTER
class NullCustomer(Customer):
    @property
    def name(self):
        return "occupant"

    @property
    def plan(self):
        return BillingPlan.basic()


customer = site.customer  # returns NullCustomer() instead of None
plan = customer.plan
name = customer.name
```

## Form Template Method

Smell: Duplicate Code in sibling subclasses.

```python
# BEFORE
class ResidentialSite:
    def bill(self):
        base = self.units * 0.5
        tax = base * SCALE
        return base + tax


class LifelineSite:
    def bill(self):
        base = self.units * 0.2
        tax = base * SCALE * 0.2
        return base + tax
```

```python
# AFTER
class Site:
    def bill(self):
        return self.base_amount() + self.tax_amount()

    def base_amount(self):
        raise NotImplementedError

    def tax_amount(self):
        raise NotImplementedError


class ResidentialSite(Site):
    def base_amount(self):
        return self.units * 0.5

    def tax_amount(self):
        return self.base_amount() * SCALE


class LifelineSite(Site):
    def base_amount(self):
        return self.units * 0.2

    def tax_amount(self):
        return self.base_amount() * SCALE * 0.2
```

## Separate Query from Modifier

Smell: a method that both answers and changes something.

```python
# BEFORE
def found_miscreant(self, people):
    for person in people:
        if person in MISCREANTS:
            self.send_alert()
            return person
    return ""
```

```python
# AFTER
def find_miscreant(self, people):
    for person in people:
        if person in MISCREANTS:
            return person
    return ""


def alert_on_miscreant(self, people):
    if self.find_miscreant(people):
        self.send_alert()
```

## Remove Middle Man

Smell: Middle Man.

```python
# BEFORE
class Person:
    def manager(self):
        return self.department.manager

    def charge_code(self):
        return self.department.charge_code

    def head_count(self):
        return self.department.head_count
```

```python
# AFTER
class Person:
    @property
    def department(self):
        return self._department


manager = john.department.manager
```

Note the tension with **Hide Delegate** above: both are valid, and which one is right depends on how much of the delegate's interface the client actually needs. Apply the one that reduces the coupling you actually have.
