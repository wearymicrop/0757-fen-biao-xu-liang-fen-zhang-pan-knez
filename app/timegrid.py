from datetime import timedelta, timezone

STEP = timedelta(minutes=5)
WINDOW = 3 * STEP
CHINA = timezone(timedelta(hours=8))


def window_starts(start, end):
    time = start
    while time < end:
        yield time
        time += WINDOW


def window_label(time):
    return time.astimezone(CHINA).strftime("%m/%d %H:%M")
