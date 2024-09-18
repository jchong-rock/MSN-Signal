from dataclasses import dataclass

@dataclass
class Configuration():
    permitted_versions = "MSNP6 MSNP2"
    debug = True
    user_database_file = None
    MSN_PORT = 1863
    SB_PORT = 1864
    IP_ADDR = "0.0.0.0"
    listeners = 5
    sb_auth_string = "17262740.1050826919.32308"