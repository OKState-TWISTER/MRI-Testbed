import sys

def catch_exceptions(func):
        def wrapper(*args, **kwargs):
            self = args[0]
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"Error: {e}")
                if not self.debug:
                    sys.exit(-1)
        return wrapper