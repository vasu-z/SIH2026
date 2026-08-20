import os
import shutil
import tempfile
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

EXTERNAL_MODFLOW_PATHS = [
    r"C:\Users\S\SIH2026\external\modflow_bin\mf6.exe",
    r"C:\Users\S\SIH2026\external\modflow_bin\mf6",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "external", "modflow_bin", "mf6.exe")),
]

def _find_mf6_executable() -> Optional[str]:
    """Locate the USGS MODFLOW 6 binary in external directory or PATH."""
    for path in EXTERNAL_MODFLOW_PATHS:
        if os.path.exists(path):
            return path
    which_path = shutil.which("mf6") or shutil.which("mf6.exe")
    if which_path:
        return which_path
    return None


class ModflowAdapter:
    """
    Isolated adapter for executing authentic USGS MODFLOW 6 groundwater-flow simulations.
    Strictly ensures physics simulations actually run through the official binary.
    """

    @classmethod
    def is_available(cls) -> bool:
        return _find_mf6_executable() is not None

    @classmethod
    def run_scenario(
        cls,
        rainfall_change_pct: float = 0.0,
        extraction_change_pct: float = 0.0,
        recharge_change_pct: float = 0.0,
        demand_change_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Build and execute a twin-run (Baseline vs Scenario) MODFLOW 6 unconfined aquifer simulation.
        """
        import flopy

        mf6_exe = _find_mf6_executable()
        if not mf6_exe:
            return {
                "engine": "MODFLOW6",
                "status": "UNAVAILABLE",
                "execution": "FAILED",
                "reason": "MODFLOW 6 executable (mf6.exe) was not found in external/modflow_bin/ or system PATH.",
                "fallback": "FAST"
            }

        start_time = time.time()
        temp_dir = tempfile.mkdtemp(prefix="jalnetra_mf6_")

        try:
            # Baseline simulation parameters
            base_recharge = 0.001       # m/day
            base_pumping = -50.0        # m3/day extraction

            # Parameterized scenario stresses
            net_recharge_factor = max(0.0, 1.0 + (rainfall_change_pct + recharge_change_pct) / 100.0)
            net_pumping_factor = max(0.0, 1.0 + (extraction_change_pct + demand_change_pct) / 100.0)

            scenario_recharge = base_recharge * net_recharge_factor
            scenario_pumping = base_pumping * net_pumping_factor

            # --- 1. Run Baseline Simulation ---
            base_heads = cls._simulate_single_model(
                sim_ws=os.path.join(temp_dir, "baseline"),
                exe_name=mf6_exe,
                recharge_val=base_recharge,
                pumping_val=base_pumping
            )

            # --- 2. Run Scenario Simulation ---
            scen_heads = cls._simulate_single_model(
                sim_ws=os.path.join(temp_dir, "scenario"),
                exe_name=mf6_exe,
                recharge_val=scenario_recharge,
                pumping_val=scenario_pumping
            )

            runtime = round(time.time() - start_time, 3)

            base_mean = round(float(base_heads.mean()), 3)
            base_min = round(float(base_heads.min()), 3)
            base_max = round(float(base_heads.max()), 3)

            scen_mean = round(float(scen_heads.mean()), 3)
            scen_min = round(float(scen_heads.min()), 3)
            scen_max = round(float(scen_heads.max()), 3)

            head_change = round(scen_mean - base_mean, 3)

            # Risk model derived from depth-to-water / head loss relative to top (50m)
            # Higher head = lower water stress risk
            base_risk = max(0, min(100, int(round((50.0 - base_mean) / 50.0 * 100))))
            scen_risk = max(0, min(100, int(round((50.0 - scen_mean) / 50.0 * 100))))
            risk_change = scen_risk - base_risk

            return {
                "engine": "MODFLOW6",
                "status": "VERIFIED",
                "execution": "SUCCESS",
                "mode": "physics",
                "baseline": {
                    "mean_groundwater": base_mean,
                    "min_groundwater": base_min,
                    "max_groundwater": base_max,
                    "risk": base_risk
                },
                "scenario": {
                    "mean_groundwater": scen_mean,
                    "min_groundwater": scen_min,
                    "max_groundwater": scen_max,
                    "risk": scen_risk
                },
                "difference": {
                    "groundwater_change": head_change,
                    "risk_change": risk_change
                },
                "assumptions": [
                    "2D unconfined aquifer with unstratified porous media",
                    "Grid discretization: 15 rows x 15 columns, cell dimension 100m x 100m",
                    "Hydraulic conductivity K = 10.0 m/day, Aquifer base = 0.0m, Ground surface = 50.0m",
                    "Constant head Dirichlet boundary conditions along east (20m) and west (28m) flanks",
                    f"Recharge rate scaled to {round(scenario_recharge, 6)} m/day ({round((net_recharge_factor - 1)*100, 1)}%)",
                    f"Pumping rate scaled to {round(scenario_pumping, 2)} m3/day ({round((net_pumping_factor - 1)*100, 1)}%)"
                ],
                "runtime_seconds": runtime
            }

        except Exception as e:
            logger.exception("MODFLOW 6 simulation execution failed:")
            return {
                "engine": "MODFLOW6",
                "status": "UNAVAILABLE",
                "execution": "FAILED",
                "reason": str(e),
                "fallback": "FAST"
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _simulate_single_model(cls, sim_ws: str, exe_name: str, recharge_val: float, pumping_val: float):
        import flopy

        os.makedirs(sim_ws, exist_ok=True)
        sim = flopy.mf6.MFSimulation(sim_name="jalnetra_sim", version="mf6", exe_name=exe_name, sim_ws=sim_ws)
        _ = flopy.mf6.ModflowTdis(sim, time_units="DAYS", nper=1, perioddata=[(30.0, 1, 1.0)])
        _ = flopy.mf6.ModflowIms(sim, complexity="SIMPLE")

        model_name = "gwf_model"
        gwf = flopy.mf6.ModflowGwf(sim, modelname=model_name, save_flows=True)

        nlay, nrow, ncol = 1, 15, 15
        _ = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol, delr=100.0, delc=100.0, top=50.0, botm=0.0)
        _ = flopy.mf6.ModflowGwfic(gwf, strt=25.0)
        _ = flopy.mf6.ModflowGwfnpf(gwf, icelltype=1, k=10.0)

        # Boundary conditions
        chd_spd = []
        for r in range(nrow):
            chd_spd.append([(0, r, 0), 28.0])
            chd_spd.append([(0, r, ncol - 1), 20.0])
        _ = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_spd)
        _ = flopy.mf6.ModflowGwfrcha(gwf, recharge={0: recharge_val})
        _ = flopy.mf6.ModflowGwfwel(gwf, stress_period_data={0: [[(0, 7, 7), pumping_val]]})
        _ = flopy.mf6.ModflowGwfoc(gwf, head_filerecord=f"{model_name}.hds", saverecord=[("HEAD", "ALL")])

        sim.write_simulation(silent=True)
        success, _ = sim.run_simulation(silent=True)
        if not success:
            raise RuntimeError("MODFLOW 6 solver did not converge or exited with non-zero code.")

        hds_path = os.path.join(sim_ws, f"{model_name}.hds")
        hds = flopy.utils.HeadFile(hds_path)
        heads = hds.get_data()
        return heads
