def rupee_format(value):
    try:
        value = float(value)
        s = "{:,.2f}".format(value)
        parts = s.split(".")
        int_part = parts[0].replace(",", "")
        decimal_part = parts[1]

        # Apply Indian formatting
        if len(int_part) > 3:
            int_part = int_part[:-3][::-1]
            int_part = ",".join([int_part[i:i+2] for i in range(0, len(int_part), 2)])[::-1] + "," + s[-6:-3]
        else:
            int_part = parts[0]

        return f"₹{int_part}.{decimal_part}"
    except (ValueError, TypeError):
        return "₹0.00"

def indian_comma_format(value):
    try:
        value = float(value)
        s = "{:,.2f}".format(value)
        parts = s.split(".")
        int_part = parts[0].replace(",", "")
        decimal_part = parts[1]

        # Apply Indian formatting
        if len(int_part) > 3:
            int_part = int_part[:-3][::-1]
            int_part = ",".join([int_part[i:i+2] for i in range(0, len(int_part), 2)])[::-1] + "," + s[-6:-3]
        else:
            int_part = parts[0]

        return f"{int_part}.{decimal_part}"
    except (ValueError, TypeError):
        return "₹0.00"
