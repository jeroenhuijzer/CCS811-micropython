import utime

# Timings
CCS811_WAIT_AFTER_RESET_US = 2000  # The CCS811 needs a wait after reset
CCS811_WAIT_AFTER_APPSTART_US = 1000  # The CCS811 needs a wait after app start

# Flags
CCS811_ERRSTAT_DATA_READY = 0x0008 # A new data sample is ready in ALG_RESULT_DATA
CCS811_ERRSTAT_APP_VALID = 0x0010 # Valid application firmware loaded
CCS811_ERRSTAT_FW_MODE = 0x0080 # Firmware is in application mode (not boot mode)
# These flags should normally be set - after a measurement. They flag data available (and valid app running).
CCS811_ERRSTAT_OK = (CCS811_ERRSTAT_DATA_READY | CCS811_ERRSTAT_APP_VALID | CCS811_ERRSTAT_FW_MODE)
# These flags could be set after a measurement. They flag data is not yet available (and valid app running).
CCS811_ERRSTAT_OK_NODATA = (CCS811_ERRSTAT_APP_VALID | CCS811_ERRSTAT_FW_MODE)

# CCS811 registers/mailboxes, all 1 byte except when stated otherwise
CCS811_STATUS = 0x00
CCS811_MEAS_MODE = 0x01
CCS811_ALG_RESULT_DATA = 0x02  # up to 8 bytes
CCS811_RAW_DATA = 0x03  # 2 bytes
CCS811_ENV_DATA = 0x05  # 4 bytes
CCS811_THRESHOLDS = 0x10  # 5 bytes
CCS811_BASELINE = 0x11  # 2 bytes
CCS811_HW_ID = 0x20
CCS811_HW_VERSION = 0x21
CCS811_FW_BOOT_VERSION = 0x23  # 2 bytes
CCS811_FW_APP_VERSION = 0x24  # 2 bytes
CCS811_ERROR_ID = 0xE0
CCS811_APP_START = 0xF4  # 0 bytes
CCS811_SW_RESET = 0xFF  # 4 bytes


class CCS811:

    def __init__(self, i2c, addr=0x5A):
        self.i2c = i2c
        self._slaveaddr = addr
        self._appversion = None

        self._eCO2 = 0
        self._eTVOC = 0
        self._raw = 0

    # Reset the CCS811, switch to app mode and check HW_ID. Returns false on problems.
    def begin(self) -> bool:
        _available = False
        # Invoke a SW reset (bring CCS811 in a know state)
        buf = bytearray([0x11, 0xE5, 0x72, 0x8A])
        self.i2c.writeto_mem(self._slaveaddr, CCS811_SW_RESET, buf)
        utime.sleep_us(CCS811_WAIT_AFTER_RESET_US)

        # Check that HW_ID is 0x81
        hw_id = self.i2c.readfrom_mem(self._slaveaddr, CCS811_HW_ID, 1)
        if hw_id[0] != 0x81:
            print("ccs811: Wrong HW_ID: ", hex(hw_id[0]))
            return _available

        # Check that HW_VERSION is 0x1X
        hw_version = self.i2c.readfrom_mem(self._slaveaddr, CCS811_HW_VERSION, 1)
        if (hw_version[0] & 0xF0) != 0x10:
            print("ccs811: Wrong HW_VERSION: ", hex(hw_version[0]))
            return _available

        # Check status (after reset, CCS811 should be in boot mode with valid app)
        status = self.i2c.readfrom_mem(self._slaveaddr, CCS811_STATUS, 1)
        if status[0] != 0x10:
            print("ccs811: Not in boot mode, or no valid app: ", hex(status[0]))
            return _available

        # Read the application version
        app_version = self.i2c.readfrom_mem(self._slaveaddr, CCS811_FW_APP_VERSION, 2)
        self._appversion = app_version[0] * 256 + app_version[1]

        # Switch CCS811 from boot mode into app mode
        buf = bytearray()
        self.i2c.writeto_mem(self._slaveaddr, CCS811_APP_START, buf)
        utime.sleep_us(CCS811_WAIT_AFTER_APPSTART_US)

        # Check if the switch was successful
        status = self.i2c.readfrom_mem(self._slaveaddr, CCS811_STATUS, 1)
        if status[0] != 0x90:
            print("ccs811: Not in boot mode, or no valid app: ", hex(status[0]))
            return _available

        _available = True
        #  Return success
        return _available

    # Switch CCS811 to `mode`, use constants CCS811_MODE_XXX.
    def start(self, mode) -> None:
        meas_mode = mode << 4
        buf = bytearray([meas_mode])
        self.i2c.writeto_mem(self._slaveaddr, CCS811_MEAS_MODE, buf)

    #  Get measurement results from the CCS811, check status via errstat, e.g. ccs811_errstat(errstat)
    def read(self) -> None:
        stat = self.i2c.readfrom_mem(self._slaveaddr, CCS811_STATUS, 1)
        if stat[0] == CCS811_ERRSTAT_OK:
            buf = self.i2c.readfrom_mem(self._slaveaddr, CCS811_ALG_RESULT_DATA, 8)

            self._eCO2 = buf[0] * 256 + buf[1]
            self._eTVOC = buf[2] * 256 + buf[3]
            self._raw = buf[6] * 256 + buf[7]
        elif stat[0] == CCS811_ERRSTAT_OK_NODATA:
            print("CCS811: waiting for (new) data")

    # Gets version of the CCS811 hardware
    def hardware_version(self) -> hex:
        version = self.i2c.readfrom_mem(self._slaveaddr, CCS811_HW_VERSION, 1)
        return hex(version[0])

    # Gets version of the CCS811 boot loader
    def bootloader_version(self) -> hex:
        version = self.i2c.readfrom_mem(self._slaveaddr, CCS811_FW_BOOT_VERSION, 2)
        return hex(version[0] * 256 + version[1])

    # Gets version of the CCS811 application
    def application_version(self) -> hex:
        version = self.i2c.readfrom_mem(self._slaveaddr, CCS811_FW_APP_VERSION, 2)
        return hex(version[0] * 256 + version[1])

    # Gets the ERROR_ID [same as 'err' part of 'errstat' in 'read']
    # Note, this actually clears CCS811_ERROR_ID (hardware feature)
    def get_errorid(self) -> hex:
        version = self.i2c.readfrom_mem(self._slaveaddr, CCS811_ERROR_ID, 1)
        return hex(version[0])