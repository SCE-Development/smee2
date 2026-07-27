import argparse

def get_args():
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="increase logging verbosity; can be used multiple times like -vvv"
    )
    parser.add_argument("--config", help="path to yaml file for api key, see readme")

    return parser.parse_args()
