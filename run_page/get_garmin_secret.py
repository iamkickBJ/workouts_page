import argparse
import garth

# Patch garth to use a browser User-Agent to bypass bot detection
garth.http.USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("email", nargs="?", help="email of garmin")
    parser.add_argument("password", nargs="?", help="password of garmin")
    parser.add_argument(
        "--is-cn",
        dest="is_cn",
        action="store_true",
        help="if garmin accout is cn",
    )
    options = parser.parse_args()
    if options.is_cn:
        garth.configure(domain="garmin.cn")
    garth.login(options.email, options.password)
    secret_string = garth.client.dumps()
    print(secret_string)
