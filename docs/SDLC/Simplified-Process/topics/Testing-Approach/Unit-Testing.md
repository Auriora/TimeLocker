# Unit Testing

Unit tests verify individual components (functions, methods, classes) in isolation. They provide fast feedback on code quality and catch issues early.

## Why It Matters

For solo developers, unit tests:
- Catch bugs early before they spread
- Build confidence when making changes
- Serve as executable documentation
- Reveal design flaws in your code
- Reduce debugging time

## Quick Start Guide

1. **Focus on critical code**:
   - Complex business logic
   - Financial/sensitive data handling
   - Frequently changed components
   - Previous bug locations

2. **Write effective tests**:
   - Keep each test small and focused
   - Use descriptive names (e.g., `test_withdrawal_exceeding_balance_raises_exception`)
   - Follow the Arrange-Act-Assert pattern

3. **Consider Test-Driven Development** for complex features:
   - Write the failing test first
   - Implement minimal code to pass
   - Refactor while keeping tests green

4. **Use mocking wisely**:
   - Mock external dependencies (APIs, databases)
   - Avoid over-mocking
   - Use dependency injection for testability

## Example Test

```python
def test_calculate_discount():
    # Arrange
    product = Product(price=100)
    customer = Customer(loyalty_years=5)
    calculator = DiscountCalculator()

    # Act
    discount = calculator.calculate(product, customer)

    # Assert
    assert discount == 10  # 10% for 5-year customers
```

## Practical Tips

- Aim for 70-80% coverage of core logic, 100% for critical paths
- Choose appropriate frameworks (pytest, Jest, JUnit, NUnit)
- Focus on behavior, not implementation details
- Keep tests fast (milliseconds, not seconds)
- Use AI to help identify edge cases and test scenarios

## Common Pitfalls

- Brittle tests that break with minor changes
- Slow tests that discourage frequent running
- Duplicate test code (use helper methods instead)
- Complex test logic (if it's hard to understand, simplify it)
- Chasing coverage numbers at the expense of quality
