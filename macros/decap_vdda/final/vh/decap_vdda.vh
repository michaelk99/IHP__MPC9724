// Blackbox of decap_vdda, power pins only. LibreLane's generated header has no `endif for a module without signal ports.
(* blackbox *)
module decap_vdda (
`ifdef USE_POWER_PINS
  inout VDD,
  inout VSS
`endif
);
endmodule
