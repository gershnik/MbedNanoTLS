//  Copyright 2024 Eugene Gershnik
//  SPDX-License-Identifier: Apache-2.0

#include <SPI.h>

#include "mbedtls/platform_time.h"

extern "C" {

    mbedtls_ms_time_t mbedtls_ms_time(void) {
        return millis();
    }

}
