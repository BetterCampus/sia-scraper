import datetime


class DateFormatter:
    def __init__(self, date: datetime.datetime) -> None:
        self.date = date

    @staticmethod
    def __pad_to_two_digits(num: int) -> str:
        """Pad integer to 2 digits with leading zero.

        ## Args
            num: Integer to pad

        ## Returns
            String with 2-digit zero-padded number
        """
        return str(num).zfill(2)

    def formatDate(self) -> str:
        """Format datetime to 'YYYY-MM-DD HH:MM' string.

        ## Args
            date: datetime object to format

        ## Returns
            Formatted date string (e.g., "2024-03-25 20:15")
        """
        year = str(self.date.year)
        month = DateFormatter.__pad_to_two_digits(self.date.month)
        day = DateFormatter.__pad_to_two_digits(self.date.day)
        hours = DateFormatter.__pad_to_two_digits(self.date.hour)
        minutes = DateFormatter.__pad_to_two_digits(self.date.minute)

        return f"{year}-{month}-{day} {hours}:{minutes}"
