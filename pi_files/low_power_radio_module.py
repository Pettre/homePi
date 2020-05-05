from flask import Flask, render_template
import datetime
import pygal
import sqlite3
from dateutil import tz 
import pandas

DATABASE_NAME = "/home/www/low_power_radio.sqlite"

def utc_to_localtime(utc_time):

    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()

    r_utc = datetime.datetime.strptime(str(utc_time), "%Y-%m-%d %H:%M:%S")
    r_localtime = r_utc.replace(tzinfo = from_zone).astimezone(to_zone) 

    return r_localtime.strftime("%Y-%m-%d %H:%M:%S")

def calc_dewpoint(temperature, humidity):
    
    c = temperature
    x = 1 - (0.01 * humidity)
    dewpoint = (14.55 + 0.114 * c) * x;
    dewpoint = dewpoint + ((2.5 + 0.007 * c) * x) ** 3;
    dewpoint = dewpoint + (15.9 + 0.117 * c) * x ** 14;
    dewpoint = c - dewpoint;

    return dewpoint

def get_radios():

    conn = sqlite3.connect(DATABASE_NAME)
    curs = conn.cursor()
    curs.execute("SELECT address, location FROM radio")
    rows = curs.fetchall()
    conn.close()

    return rows 

def get_data(values, radio_address, hours):

    conn = sqlite3.connect(DATABASE_NAME)
    curs = conn.cursor()
    curs.execute("SELECT %s FROM data WHERE \
                 timestamp>datetime('now','-%i hours') AND address=%i" 
                 % (values, hours, radio_address)
                )

    rows = curs.fetchall()
    conn.close()

    return rows

def render_charts(hours_to_chart, interval):

    temperature_chart = pygal.Line(x_label_rotation=20) #, show_dots=False)
    temperature_chart.title = "Temperaturer siste %d timer" %hours_to_chart

    humidity_chart = pygal.Line(x_label_rotation=20) #, show_dots=False)
    humidity_chart.title = "Fukt siste %i timer" %hours_to_chart

    for radio_address, radio_location in get_radios():
        rows = get_data("timestamp, temperature, humidity",
                        radio_address, hours_to_chart)

        data_frame = pandas.DataFrame(rows)
        data_frame.columns = ["time", "temperature", "humidity"]
        data_frame.index = pandas.to_datetime(data_frame.pop("time"), utc=True)

        resampled_data = data_frame
        resampled_data = data_frame.resample(interval, how='mean')

        time_stamps = [utc_to_localtime(x) for x in resampled_data.index.tolist()]

        temperature_chart.x_labels = time_stamps
        humidity_chart.x_labels = time_stamps

        temperature_chart.add(radio_location, resampled_data.temperature.tolist())
        humidity_chart.add(radio_location, resampled_data.humidity.tolist())

    return (temperature_chart.render(is_unicode=True, height=400),
            humidity_chart.render(is_unicode=True, height=400))

def gpio_input_changes(radio_address):

    rows = get_data("timestamp, input", radio_address, 500)
    
    try:
        pressed_released = [[utc_to_localtime(rows[0][0]),rows[0][1]]]

        for n in rows:
            if n[1] != pressed_released[-1][1]:
                pressed_released.append([utc_to_localtime(n[0]), n[1]])

        if len(pressed_released) > 10:
            pressed_released = pressed_released[-10:]

        pressed_released_text = [[x[0], "pressed"] if x[1] > 0 else
                                 [x[0], "released"] for x in pressed_released] 

        pressed_released = pressed_released_text

    except:
        pressed_released = [[0]["unknown"]]


    return pressed_released

low_power_radio = Flask(__name__)
@low_power_radio.route("/")

def fill_template_main():

    time_string = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")     

    temperature_chart_24_hours, humidity_chart_24_hours = render_charts(24, '1H')

    template_data = {
        "title"         : "Raspberry Pi",
        "time"          : time_string,
        "list"          : gpio_input_changes(int(0x2075)),
        "chart_t_24"    : temperature_chart_24_hours,
        "chart_h_24"    : humidity_chart_24_hours
    }

    return render_template("main.html", **template_data)
 
if __name__ == "__main__":
    low_power_radio.run(host="0.0.0.0", debug=True)
