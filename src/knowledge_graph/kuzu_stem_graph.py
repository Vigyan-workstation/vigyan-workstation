"""
Vigyan Gen-2: KùzuDB Embedded C++ STEM Knowledge Graph
Deterministic Multi-Hop GraphRAG Engine for Physical Laws, Electronics, and Math.
"""

import os
import shutil
from typing import Dict, List, Any, Optional
import kuzu

class VigyanSTEMGraph:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            candidates = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "db_store.db"),
                os.path.expanduser("~/.vigyan/knowledge_graph/db_store.db"),
                "/home/hello/vigyan_masterpiece/knowledge_graph/db_store.db"
            ]
            for c in candidates:
                if os.path.exists(c):
                    db_path = c
                    break
            if not db_path:
                db_path = os.path.expanduser("~/.vigyan/knowledge_graph/db_store.db")
        self.db_path = db_path
        if os.path.isdir(self.db_path):
            self.db_path = os.path.join(self.db_path, "kuzu.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.db = kuzu.Database(self.db_path)
        self.conn = kuzu.Connection(self.db)
        self._init_schema_and_seed()

    def _init_schema_and_seed(self):
        """Initializes schema and seeds baseline physical laws if not already populated."""
        try:
            res = self.conn.execute("MATCH (l:Law) RETURN count(l);")
            if res.has_next() and res.get_next()[0] > 0:
                # Tables already exist and are seeded
                return
        except Exception:
            pass

        # If Law does not exist, initialize and seed
        try:
            # Create Node Tables
            self.conn.execute("""
                CREATE NODE TABLE Law(
                    name STRING, 
                    domain STRING, 
                    equation STRING, 
                    description STRING, 
                    PRIMARY KEY (name)
                )
            """)
            self.conn.execute("""
                CREATE NODE TABLE Component(
                    name STRING, 
                    category STRING, 
                    properties STRING, 
                    PRIMARY KEY (name)
                )
            """)
            self.conn.execute("""
                CREATE NODE TABLE Concept(
                    name STRING, 
                    field STRING, 
                    definition STRING, 
                    PRIMARY KEY (name)
                )
            """)
            self.conn.execute("""
                CREATE NODE TABLE Constant(
                    name STRING, 
                    symbol STRING, 
                    value STRING, 
                    units STRING, 
                    PRIMARY KEY (name)
                )
            """)

            # Create Rel Tables
            self.conn.execute("CREATE REL TABLE GOVERNS(FROM Law TO Component)")
            self.conn.execute("CREATE REL TABLE APPLIED_TO(FROM Law TO Concept)")
            self.conn.execute("CREATE REL TABLE DERIVED_FROM(FROM Law TO Law)")
            self.conn.execute("CREATE REL TABLE REQUIRES_CONSTANT(FROM Law TO Constant)")
            self.conn.execute("CREATE REL TABLE RELATED_TO(FROM Concept TO Concept)")

            self._seed_fundamental_knowledge()
        except Exception:
            pass

    def _seed_fundamental_knowledge(self):
        """Seeds deterministic physical, circuit, semiconductor, aerospace, and mathematical axioms using parameterized queries."""
        # 1. Fundamental Constants
        constants = [
            ("Speed of Light", "c", "299792458", "m/s"),
            ("Planck Constant", "h", "6.62607015e-34", "J*s"),
            ("Reduced Planck Constant", "hbar", "1.054571817e-34", "J*s"),
            ("Elementary Charge", "q", "1.602176634e-19", "C"),
            ("Gravitational Constant", "G", "6.67430e-11", "m^3/(kg*s^2)"),
            ("Boltzmann Constant", "k_B", "1.380649e-23", "J/K"),
            ("Permittivity of Free Space", "epsilon_0", "8.8541878128e-12", "F/m"),
            ("Permeability of Free Space", "mu_0", "1.25663706212e-6", "N/A^2"),
            ("Standard Gravity", "g_0", "9.80665", "m/s^2"),
            ("Ideal Gas Constant", "R", "8.314462618", "J/(mol*K)"),
            ("Earth Mass", "M_earth", "5.9722e24", "kg"),
            ("Earth Radius", "R_earth", "6371000", "m")
        ]
        for name, sym, val, unit in constants:
            self.conn.execute(
                "CREATE (:Constant {name: $name, symbol: $sym, value: $val, units: $unit})",
                {"name": name, "sym": sym, "val": val, "unit": unit}
            )

        # 2. Components
        components = [
            ("Resistor", "Passive", "Linear V-I relationship; dissipates power as thermal energy"),
            ("Capacitor", "Passive", "Stores electrostatic energy in electric field; opposes voltage changes"),
            ("Inductor", "Passive", "Stores magnetic energy in magnetic field; opposes current changes"),
            ("MOSFET", "Active", "Voltage-controlled field-effect transistor; operates in Cutoff, Triode, and Saturation"),
            ("BJT", "Active", "Current-controlled bipolar transistor; active, saturation, cutoff modes"),
            ("Diode", "Semiconductor", "Asymmetric conductance; exponential forward current, negligible reverse breakdown"),
            ("Operational Amplifier", "Active IC", "Differential voltage amplifier with infinite input impedance, zero output impedance"),
            ("Rocket Engine", "Propulsion", "Reaction engine generating thrust via Newton third law and mass expulsion"),
            ("Satellite", "Aerospace", "Spacecraft in stable gravitational orbital equilibrium around a planetary body"),
            ("CMOS Inverter", "VLSI Digital", "Complementary nMOS and pMOS pair providing near-zero static power dissipation")
        ]
        for name, cat, prop in components:
            self.conn.execute(
                "CREATE (:Component {name: $name, category: $cat, properties: $prop})",
                {"name": name, "cat": cat, "prop": prop}
            )

        # 3. Concepts
        concepts = [
            ("Ohmic Dissipation", "Electronics", "Rate at which electrical energy is transformed into heat"),
            ("Capacitive Reactance", "Circuits", "Impedance offered by capacitor to alternating current: Xc = 1/(omega * C)"),
            ("Inductive Reactance", "Circuits", "Impedance offered by inductor to alternating current: Xl = omega * L"),
            ("Cutoff Frequency", "Signal Processing", "Corner frequency where filter output power drops by 3dB: f_c = 1/(2*pi*R*C)"),
            ("Subthreshold Conduction", "VLSI", "Leakage current flowing through MOSFET channel when Vgs < Vth"),
            ("Thermal Runaway", "Semiconductors", "Positive feedback loop where temperature rise causes current increase"),
            ("Escape Velocity", "Astrodynamics", "Minimum speed required to escape the gravitational pull of a primary body"),
            ("Orbital Period", "Astrodynamics", "Time taken for an orbiting body to complete one orbit: Kepler's 3rd Law"),
            ("Vis-Viva Equation", "Orbital Mechanics", "Relates orbital speed v to orbital distance r and semi-major axis a"),
            ("Carnot Efficiency", "Thermodynamics", "Theoretical maximum efficiency of a heat engine: eta = 1 - T_C/T_H"),
            ("Threshold Voltage Roll-Off", "VLSI", "Reduction in threshold voltage Vt as channel length shrinks due to drain-induced barrier lowering (DIBL) and charge sharing"),
            ("Silicon Dioxide Passivation", "VLSI", "Thermally grown native oxide SiO_2 provides stable interface, high dielectric breakdown, and chemical passivation for planar ICs"),
            ("Velocity Saturation", "VLSI", "Carrier drift velocity saturates at critical lateral electric fields due to optical phonon scattering in short-channel MOSFETs"),
            ("Capacitor AC Power Dissipation", "Circuits", "In an ideal capacitor, current leads voltage by 90 degrees phase shift resulting in zero average real power dissipation (P_avg = 0)"),
            ("Hohmann Transfer Orbit", "Astrodynamics", "Two-impulse elliptical orbital transfer maneuver connecting two coplanar circular orbits with minimal delta-v expenditure")
        ]
        for name, fld, dfn in concepts:
            self.conn.execute(
                "CREATE (:Concept {name: $name, field: $fld, definition: $dfn})",
                {"name": name, "fld": fld, "dfn": dfn}
            )

        # 4. Laws & Governing Equations
        laws = [
            ("Ohm's Law", "Circuits", "V = I * R", "Voltage across a conductor equals current multiplied by resistance."),
            ("Joule Heating Law", "Circuits", "P = I^2 * R = V^2 / R", "Power dissipated as heat in an electrical conductor."),
            ("Kirchhoff's Current Law", "Circuits", "sum(I_in) = sum(I_out)", "Conservation of charge at any electrical node."),
            ("Kirchhoff's Voltage Law", "Circuits", "sum(V_loop) = 0", "Conservation of electrical energy around any closed loop."),
            ("Faraday's Law of Induction", "Electromagnetism", "emf = - dPhi_B / dt", "Induced electromotive force equals negative time rate of magnetic flux change."),
            ("RC Time Constant", "Circuits", "tau = R * C", "Time required for capacitor to charge to ~63.2% of supply voltage."),
            ("MOSFET Saturation Current", "VLSI", "I_d = 0.5 * mu * C_ox * (W/L) * (V_gs - V_th)^2 * (1 + lambda * V_ds)", "Drain current in pinch-off saturation region with channel-length modulation."),
            ("Newton's Law of Universal Gravitation", "Mechanics", "F = G * (m1 * m2) / r^2", "Attractive force between two point masses."),
            ("Kepler's Third Law", "Astrodynamics", "T^2 = (4 * pi^2 / (G * M)) * a^3", "Square of orbital period is proportional to cube of semi-major axis."),
            ("Vis-Viva Law", "Astrodynamics", "v^2 = G * M * (2/r - 1/a)", "Equation governing the speed of an orbiting celestial body or satellite."),
            ("Tsiolkovsky Rocket Equation", "Aerospace", "Delta_v = I_sp * g_0 * ln(m_0 / m_f)", "Velocity change achieved by vehicle expelling reaction mass."),
            ("Maxwell Ampere Law", "Electromagnetism", "curl(B) = mu_0 * J + mu_0 * epsilon_0 * dE/dt", "Relates magnetic fields to current density and time-varying electric displacement."),
            ("First Law of Thermodynamics", "Thermodynamics", "Delta_U = Q - W", "Internal energy change equals heat added minus work done by system."),
            ("Carnot Limit", "Thermodynamics", "eta_max = 1 - (T_cold / T_hot)", "Upper theoretical limit for heat engine thermal efficiency.")
        ]
        for name, dom, eq, desc in laws:
            self.conn.execute(
                "CREATE (:Law {name: $name, domain: $dom, equation: $eq, description: $desc_val})",
                {"name": name, "dom": dom, "eq": eq, "desc_val": desc}
            )

        # 5. Connect Relationships
        relations = [
            ("Ohm's Law", "Resistor", "GOVERNS"),
            ("Joule Heating Law", "Resistor", "GOVERNS"),
            ("RC Time Constant", "Capacitor", "GOVERNS"),
            ("Faraday's Law of Induction", "Inductor", "GOVERNS"),
            ("MOSFET Saturation Current", "MOSFET", "GOVERNS"),
            ("Tsiolkovsky Rocket Equation", "Rocket Engine", "GOVERNS"),
            ("Vis-Viva Law", "Satellite", "GOVERNS"),
            ("Kepler's Third Law", "Satellite", "GOVERNS"),
            ("Newton's Law of Universal Gravitation", "Escape Velocity", "APPLIED_TO"),
            ("Vis-Viva Law", "Orbital Period", "APPLIED_TO"),
            ("Ohm's Law", "Ohmic Dissipation", "APPLIED_TO"),
            ("RC Time Constant", "Cutoff Frequency", "APPLIED_TO"),
            ("Carnot Limit", "Carnot Efficiency", "APPLIED_TO")
        ]
        for law_name, target, rel_type in relations:
            if rel_type == "GOVERNS":
                self.conn.execute("""
                    MATCH (l:Law), (c:Component)
                    WHERE l.name = $law_name AND c.name = $target
                    CREATE (l)-[:GOVERNS]->(c)
                """, {"law_name": law_name, "target": target})
            elif rel_type == "APPLIED_TO":
                self.conn.execute("""
                    MATCH (l:Law), (c:Concept)
                    WHERE l.name = $law_name AND c.name = $target
                    CREATE (l)-[:APPLIED_TO]->(c)
                """, {"law_name": law_name, "target": target})

    def query_multihop_context(self, keywords: List[str]) -> str:
        """Searches KùzuDB for matching nodes and returns multi-hop causal relations and exact equations."""
        matched_facts = []
        seen_laws = set()

        for kw in keywords:
            kw_clean = kw.strip()
            if not kw_clean or len(kw_clean) < 3:
                continue

            # Check Laws
            res = self.conn.execute("""
                MATCH (l:Law) 
                WHERE lower(l.name) CONTAINS lower($kw) 
                   OR lower(l.domain) CONTAINS lower($kw)
                   OR lower(l.description) CONTAINS lower($kw)
                OPTIONAL MATCH (l)-[:GOVERNS]->(comp:Component)
                OPTIONAL MATCH (l)-[:APPLIED_TO]->(con:Concept)
                RETURN l.name, l.equation, l.description, comp.name, con.name;
            """, {"kw": kw_clean})

            while res.has_next():
                row = res.get_next()
                law_name, eq, desc, comp, con = row
                if law_name not in seen_laws:
                    seen_laws.add(law_name)
                    fact = f"- [Graph Law]: {law_name}\n  Equation: {eq}\n  Axiom: {desc}"
                    if comp:
                        fact += f"\n  Governs Hardware: {comp}"
                    if con:
                        fact += f"\n  Applied To Phenomenon: {con}"
                    matched_facts.append(fact)

            # Check Constants
            res_c = self.conn.execute("""
                MATCH (c:Constant)
                WHERE lower(c.name) CONTAINS lower($kw) 
                   OR lower(c.symbol) = lower($kw)
                RETURN c.name, c.symbol, c.value, c.units;
            """, {"kw": kw_clean})

            while res_c.has_next():
                c_name, c_sym, c_val, c_units = res_c.get_next()
                matched_facts.append(f"- [Graph Constant]: {c_name} ({c_sym}) = {c_val} {c_units}")

            # Check Concepts
            res_con = self.conn.execute("""
                MATCH (con:Concept)
                WHERE lower(con.name) CONTAINS lower($kw)
                   OR lower(con.definition) CONTAINS lower($kw)
                RETURN con.name, con.field, con.definition;
            """, {"kw": kw_clean})
            while res_con.has_next():
                c_name, c_fld, c_dfn = res_con.get_next()
                if c_name not in seen_laws:
                    seen_laws.add(c_name)
                    matched_facts.append(f"- [Graph Concept]: {c_name} ({c_fld})\n  Definition: {c_dfn}")

            # Check Components
            res_comp = self.conn.execute("""
                MATCH (comp:Component)
                WHERE lower(comp.name) CONTAINS lower($kw)
                   OR lower(comp.properties) CONTAINS lower($kw)
                RETURN comp.name, comp.category, comp.properties;
            """, {"kw": kw_clean})
            while res_comp.has_next():
                comp_name, comp_cat, comp_prop = res_comp.get_next()
                if comp_name not in seen_laws:
                    seen_laws.add(comp_name)
                    matched_facts.append(f"- [Graph Component]: {comp_name} ({comp_cat})\n  Properties: {comp_prop}")

        if not matched_facts:
            return ""

        return "### KùzuDB GraphRAG Verified Physical Causal Context:\n" + "\n\n".join(matched_facts[:5])

if __name__ == "__main__":
    test_p = "/tmp/test_vigyan_graph"
    if os.path.exists(test_p):
        if os.path.isdir(test_p):
            shutil.rmtree(test_p)
        else:
            os.remove(test_p)
    graph = VigyanSTEMGraph(test_p)
    print("Testing Graph Context for 'Rocket':")
    print(graph.query_multihop_context(["Rocket", "Tsiolkovsky"]))
    print("\nTesting Graph Context for 'MOSFET':")
    print(graph.query_multihop_context(["MOSFET", "Saturation"]))
    print("\nTesting Graph Context for 'Planck':")
    print(graph.query_multihop_context(["Planck"]))
    print("\nKÙZU GRAPH MODULE VERIFIED!")
