from tcp import TCPServer
import msn_handler
import auth.user_database
import auth.login
from config import Configuration
from msn_patcher import ErrorPatcher
from multiprocessing import Process
from switchboard.patcher import SwitchBoardFactory

def main():
    handler = msn_handler.MSNHandler
    login_database = auth.user_database.MD5JSON(Configuration.user_database_file)
    switchboard_factory = SwitchBoardFactory(login_database)
    switchboard_server = TCPServer(handler, [switchboard_factory, ErrorPatcher], port=Configuration.SB_PORT)
    login_database.set_switchboard((switchboard_server.ip, switchboard_server.port))
    login_factory = auth.login.MD5LoginFactory(login_database)
    notification_server = TCPServer(handler, [login_factory, ErrorPatcher])

    notification_server.start()
    switchboard_server.start()

    notification_server.join()
    switchboard_server.join()

if __name__ == "__main__":
    main()