# MbedNanoTLS

Arduino Mbed OS Nano boards provide a version of Mbed TLS within their board library. 

However, this version is old and slow. A much better performance (and likely less vulnerabilities) can be achieved by using the latest version of Mbed OS. However, simply trying to build and use the latest version will not work since its symbols clash with the ones provided by the board library. Additionally Mbed TLS achieves best performance when built with `-O3` rather than `-Os` optimizations which can be tricky to accomplish in environments such as Arduino IDE.

This library solves these problems. It packages the latest release (currently 3.6.0 LTS) of Mbed TLS, makes it build with `-O3` optimizations regardless of an IDE/build system used and makes its symbols not clash with the system ones. 

## Usage

```cpp
#include "MbedNanoTLS.h"
```

Then use Mbed TLS according to its documentation. `MbedNanoTLS.h` includes some common Mbed TLS headers. If you need additional ones simply do:

```cpp
#include <mbedtls/header_name.h>
```

## How it is made

You can see the details on how this library is produced from Mbed TLS sources in [`.tools/prepare.py`](.tools/prepare.py) script. If desired, you can also re-create this library using it.

## License

<pre>
Copyright 2024 Eugene Gershnik

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
</pre>
