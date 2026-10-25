# DC supply current of the IO cells

| cell | rail | pad and input | IOVDD (nA) | rail (nA) |
|---|---|---|---|---|
| sg13cmos5l_IOPadAnalog | VDD | low | 0.091 | -0.000 |
| sg13cmos5l_IOPadAnalog | VDD | high | 0.044 | -0.000 |
| sg13cmos5l_IOPadAnalog | VDDA | low | 0.091 | -0.000 |
| sg13cmos5l_IOPadAnalog | VDDA | high | 0.039 | -0.000 |
| sg13cmos5l_IOPadIOVdd | VDD | idle | 0.660 | -0.000 |
| sg13cmos5l_IOPadIOVss | VDD | idle | 0.020 | -0.000 |
| sg13cmos5l_IOPadIn | VDD | low | 0.038 | 0.273 |
| sg13cmos5l_IOPadIn | VDD | high | 0.008 | 0.182 |
| sg13cmos5l_IOPadIn | VDDA | low | 0.038 | 0.675 |
| sg13cmos5l_IOPadIn | VDDA | high | 0.008 | 0.303 |
| sg13cmos5l_IOPadInOut30mA | VDD | low | 0.107 | 1.524 |
| sg13cmos5l_IOPadInOut30mA | VDD | high | 0.030 | 1.291 |
| sg13cmos5l_IOPadOut30mA | VDD | idle | 0.572 | 0.362 |
| sg13cmos5l_IOPadOut4mA | VDDA | idle | 0.536 | 0.603 |
| sg13cmos5l_IOPadVdd | VDD | idle | -0.000 | 0.225 |
| sg13cmos5l_IOPadVdd | VDDA | idle | -0.000 | 0.278 |
| sg13cmos5l_IOPadVss | VDD | idle | 0.020 | -0.000 |
| sg13cmos5l_ip__clamp_vddvss | VDD | idle | -0.000 | 0.029 |
| sg13cmos5l_ip__clamp_vddvss | VDDA | idle | -0.000 | 0.032 |

Predicted static current in the DSA1 state, from the cell counts:

- this chip: IOVDD 3.29 nA, VDD 2.35 nA, VDDA 2.00 nA
- tapeout/v1.1.1: IOVDD 11.39 nA, VDD 10.95 nA
