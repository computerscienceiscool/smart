# import 
import stubs
import os
from stubs import unit

# ====================================================
# ====================================================
cwd = os.getcwd()

# Load in model and settings
config          = stubs.config.Config()
pc, sc, cc, rc  = stubs.common.read_smodel('lin_deg.smodel')

# Define solvers
mps             = stubs.solvers.MultiphysicsSolver('iterative', eps_Fabs=1e-8)
nls             = stubs.solvers.NonlinearNewtonSolver(relative_tolerance=1e-6, absolute_tolerance=1e-8,
                                          dt_increase_factor=1.05, dt_decrease_factor=0.7)
ls              = stubs.solvers.DolfinKrylovSolver(method = 'bicgstab', preconditioner='hypre_amg')
solver_system   = stubs.solvers.SolverSystem(final_t = 0.4, initial_dt = 0.01, adjust_dt = [(0.2, 0.02)],
                                           multiphysics_solver=mps, nonlinear_solver=nls, linear_solver=ls)

# Load parent mesh
parent_mesh = stubs.mesh.ParentMesh(mesh_filename=cwd+'/cell2013_3d/cube_10.xml')

model = stubs.model.Model(pc, sc, cc, rc, config, solver_system, parent_mesh)
model.initialize_refactor()

# solve system
model.solve(store_solutions=False)
