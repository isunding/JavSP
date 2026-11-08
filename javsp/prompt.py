import sys

from javsp.config import Cfg
def prompt(message: str, what: str) -> str:
    if Cfg().other.interactive:
        return input(message)
    else:
        print(f"缺少{what}")
        # 打包成 exe 后 site 内置的 exit() 不存在，必须用 sys.exit
        sys.exit(1)
