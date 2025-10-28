"""
Simple calculator module
Provides basic mathematical functions for demonstrating test case writing
"""

class Calculator:
    """Calculator class that provides basic mathematical operations"""
    
    def add(self, a, b):
        """
        Calculate the sum of two numbers
        
        Args:
            a (int/float): First number
            b (int/float): Second number
        
        Returns:
            int/float: Sum of the two numbers
        """
        return a + b

    def subtract(self, a, b):
        """
        Calculate the difference of two numbers
        
        Args:
            a (int/float): Minuend
            b (int/float): Subtrahend
        
        Returns:
            int/float: Difference of the two numbers
        """
        return a - b

    def multiply(self, a, b):
        """
        Calculate the product of two numbers
        
        Args:
            a (int/float): First number
            b (int/float): Second number
        
        Returns:
            int/float: Product of the two numbers
        """
        return a * b

    def divide(self, a, b):
        """
        Calculate the quotient of two numbers
        
        Args:
            a (int/float): Dividend
            b (int/float): Divisor
        
        Returns:
            float: Quotient of the two numbers
        
        Raises:
            ValueError: When divisor is zero
        """
        if b == 0:
            raise ValueError("Divisor cannot be zero")
        return a / b


def add(a, b):
    """
    Calculate the sum of two numbers
    
    Args:
        a (int/float): First number
        b (int/float): Second number
    
    Returns:
        int/float: Sum of the two numbers
    """
    return a + b

def subtract(a, b):
    """
    Calculate the difference of two numbers
    
    Args:
        a (int/float): Minuend
        b (int/float): Subtrahend
    
    Returns:
        int/float: Difference of the two numbers
    """
    return a - b

def multiply(a, b):
    """
    Calculate the product of two numbers
    
    Args:
        a (int/float): First number
        b (int/float): Second number
    
    Returns:
        int/float: Product of the two numbers
    """
    return a * b

def divide(a, b):
    """
    Calculate the quotient of two numbers
    
    Args:
        a (int/float): Dividend
        b (int/float): Divisor
    
    Returns:
        float: Quotient of the two numbers
    
    Raises:
        ZeroDivisionError: When divisor is zero
    """
    if b == 0:
        raise ZeroDivisionError("Divisor cannot be zero")
    return a / b

def is_even(number):
    """
    Check if a number is even
    
    Args:
        number (int): Number to check
    
    Returns:
        bool: True if the number is even, False otherwise
    """
    if not isinstance(number, int):
        raise TypeError("Input must be an integer")
    return number % 2 == 0

if __name__ == "__main__":
    # Simple demonstration
    calc = Calculator()
    print("Using Calculator class:")
    print("Addition: 3 + 5 =", calc.add(3, 5))
    print("Subtraction: 10 - 3 =", calc.subtract(10, 3))
    print("Multiplication: 4 * 6 =", calc.multiply(4, 6))
    print("Division: 15 / 3 =", calc.divide(15, 3))
    
    print("\nUsing standalone functions:")
    print("Addition: 3 + 5 =", add(3, 5))
    print("Subtraction: 10 - 3 =", subtract(10, 3))
    print("Multiplication: 4 * 6 =", multiply(4, 6))
    print("Division: 15 / 3 =", divide(15, 3))
    print("Even number check: Is 4 even?", is_even(4))
    print("Even number check: Is 5 even?", is_even(5))