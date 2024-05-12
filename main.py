
import pmdarima as pm
from fake_useragent import UserAgent
import pandas as pd
import matplotlib.pyplot as plt


# Global vars
CSV_URL = "https://nordpool.didnt.work/nordpool-excel.csv"
HEADERS = {
    "User-Agent": UserAgent().random
}
ARIMA_ORDERS: tuple[tuple[int, int, int], tuple[int, int, int, int]] = None  # Here is best arima orders you would notice so that don't study model again


def index2date_time(i: str) -> tuple[tuple[str, str, str], str]:
    date, time = i.split(' ')
    year, month, day = date.split('-')
    hour = time.split(':')[0]
    return (year, month, day), hour


def prepare_data() -> pd.DataFrame:  # Preparing data
    prices: pd.DataFrame = pd.read_csv(CSV_URL, delimiter=';', storage_options=HEADERS)

    # Delete rudimentary column
    del prices["ts_end"]

    # Make from "ts_start" column to "date" index and delete previous one
    prices.index = prices["ts_start"]
    prices.index.name = "date"
    del prices["ts_start"]

    # Flip the data frame
    prices = prices.reindex(index=prices.index[::-1])

    # Trim the data frame to maintain seasonality
    prices = prices.drop(prices.index[-1], axis='index')  # Should check that the first data goes from 00:00:00
    prices = prices.drop(prices.index[:23], axis='index')  # Should check that last data ends on 23:00:00

    return prices


def forecast(prices: pd.DataFrame, days_to_predict: int) -> pd.DataFrame:
    # Model studying or modeling by orders
    if ARIMA_ORDERS is None:
        arima_model = pm.auto_arima(
            y=list(prices["price"]),
            start_p=1, start_q=1,
            max_p=5, max_q=5,

            seasonal=True, m=24,
            start_P=0, start_Q=0,
            max_P=2, max_Q=4,

            start_d=0, star_D=0,
            max_D=2, max_d=2,
            alpha=.05,
            test='kpss',
            seasonal_test='ocsb',

            trace=True,
            error_action='ignore',
            suppress_warnings=True,
            stepwise=False,
            n_fits=100,
            information_criterion='bic',
            out_of_sample_size=7,
            #scoring='mae'
        )
        print(arima_model.summary())
    else:
        arima_model = pm.ARIMA(order=ARIMA_ORDERS[0], seasonal_order=ARIMA_ORDERS[1])
        arima_model.fit(list(prices["price"]))

    # Predicting
    prices_pred, ci_pred = arima_model.predict(
        n_periods=days_to_predict * 24,
        return_conf_int=True
    )

    # Convert forecast to data
    index = []

    date_time = index2date_time(prices.index[-1])
    year = date_time[0][0]  # Be sure that predicted days are NOT next year
    month = date_time[0][1]  # Be sure that predicted daya are NOT next month
    day = date_time[0][2]

    day_i = 1
    hour_num = -1
    for i in range(len(prices_pred)):
        hour_num += 1
        if hour_num < 10:
            hour_str = "0" + str(hour_num)
        else:
            hour_str = str(hour_num)

        if int(day) + day_i < 9:
            day_str = "0" + str(int(day) + day_i)
        else:
            day_str = str(int(day) + day_i)

        index.append(
            year + '-' + month + '-' + day_str + ' ' + hour_str + ":00:00"
        )

        if hour_num >= 23:
            hour_num = 0
            day_i += 1

    forecast_data = pd.DataFrame(
        {
            'price': prices_pred,
            'ci_low': [ci[0] for ci in ci_pred],
            'ci_high': [ci[1] for ci in ci_pred]
        },
        index=index
    )

    return forecast_data


def render(prices: pd.DataFrame, forecast_data: pd.DataFrame):
    plt.figure()

    x1 = []
    for i in prices.index[-72:]:
        date_time = index2date_time(i)
        x1.append(date_time[0][2] + ", " + date_time[1])
    x2 = []
    for i in forecast_data.index:
        date_time = index2date_time(i)
        x2.append(date_time[0][2] + ", " + date_time[1])

    plot = plt.plot(x1, prices.loc[prices.index[-72:], "price"], 'c-', x2, forecast_data["price"], 'r-')

    plt.fill_between(
        x=plot[-1].get_xdata(),
        y1=forecast_data["ci_low"],
        y2=forecast_data["ci_high"],
        alpha=.2,
        color=plot[-1].get_color(),
        label=f"Prediction"
    )

    date_time = index2date_time(forecast_data.index[-1])
    plt.suptitle(
        "Last 3 days + Predicted\n"
        f'{date_time[0][0]}-{date_time[0][1]}'
    )


def main():
    prices = prepare_data()
    forecast_data = forecast(prices, 1)
    render(prices, forecast_data)
    plt.show()


if __name__ == "__main__":
    main()
