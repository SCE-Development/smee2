import argparse

def get_args():
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="increase logging verbosity; can be used multiple times"
    )

    parser.add_argument(
    "--pushgateway-url",
    default="http://127.0.0.1:9091",
    help="URL of the Prometheus Pushgateway"
    )

    return parser.parse_args()
