"""
Functions to create meshes for demos.

:func:`create_cubes` defines a 'cube-in-a-cube' mesh using the
built in :class:`dolfin.UnitCubeMesh()`, with subdomains defined and
marked by :func:`facet_topology` and :func:`cube_condition`
:func:`create_spheres`, :func:`create_ellipsoids`,
:func:`create_cylinders`, and :func:`create_ellipses`
define meshes using gmsh, which are then converted to
dolfin meshes using :func:`gmsh_to_dolfin`
:func:`write_mesh` writes 3d meshes with cell markers ``mf3`` and
facet markers ``mf2`` to hdf5 and pvd files.
"""

from typing import Tuple
import pathlib
import numpy as np
import sympy as sym
import dolfin as d
from mpi4py import MPI
from sympy.parsing.sympy_parser import parse_expr
from sympy.solvers.solveset import solveset_real

__all__ = [
    "implicit_axisymm",
    "facet_topology",
    "cube_condition",
    "create_cubes",
    "create_spheres",
    "create_ellipsoids",
    "create_axisymm",
    "create_cylinders",
    "create_ellipses",
    "create_2Dcell",
    "gmsh_to_dolfin",
    "write_mesh",
]


def implicit_axisymm(boundExpr):
    outerExpr0 = parse_expr(boundExpr)
    r = sym.Symbol("r", real=True)
    z = sym.Symbol("z", real=True)
    outerExpr0 = outerExpr0.subs({"r": 0, "z": z})
    z0 = solveset_real(outerExpr0, z)
    rVals = [0.0]
    zVals = [float(max(z0))]
    sGap = max(z0) / 100
    curTan = [1, 0]
    while rVals[-1] >= 0 and zVals[-1] >= 0:
        rNext = rVals[-1] + curTan[0] * sGap
        zNext = zVals[-1] + curTan[1] * sGap
        exprCur = parse_expr(boundExpr)
        exprCur = exprCur.subs({"r": rNext, "z": z})
        zNextSol = list(solveset_real(exprCur, z))
        zNextList = [0] * len(zNextSol)
        for i in range(len(zNextSol)):
            zNextList[i] = abs(zNextSol[i] - zNext)
        if zNextSol == [] or min(zNextList) > sGap:
            exprCur = parse_expr(boundExpr)
            exprCur = exprCur.subs({"r": r, "z": zNext})
            rNextSol = list(solveset_real(exprCur, r))
            rNextList = [0] * len(rNextSol)
            for i in range(len(rNextSol)):
                rNextList[i] = abs(rNextSol[i] - rNext)
            idx = rNextList.index(min(rNextList))
            if rNextSol == [] or min(rNextList) > sGap:
                ValueError("Next point could not be found")
            rNext = rNextSol[idx]
        else:
            idx = zNextList.index(min(zNextList))
            zNext = zNextSol[idx]
        rVals.append(float(rNext))
        zVals.append(float(zNext))
        curTan = np.array([rVals[-1] - rVals[-2], zVals[-1] - zVals[-2]])
        curTan = curTan / np.sqrt(float(curTan[0] ** 2 + curTan[1] ** 2))
    if rVals[-1] < 0:
        rVals[-1] = 0
        zVals[-1] = zVals[-2] + (zVals[-1] - zVals[-2]) * (0 - rVals[-2]) / (rVals[-1] - rVals[-2])
    elif zVals[-1] < 0:
        zVals[-1] = 0
        rVals[-1] = rVals[-2] + (rVals[-1] - rVals[-2]) * (0 - zVals[-2]) / (zVals[-1] - zVals[-2])
    rVals = np.array(rVals)
    zVals = np.array(zVals)
    return (rVals, zVals)


def facet_topology(f: d.Facet, mf3: d.MeshFunction):
    """
    Given a facet and cell mesh function,
    return the topology of the face
    as either 'boundary' (outer boundary),
    'internal', or 'interface' (boundary of inner cube)
    """
    # cells adjacent face
    localCells = [mf3.array()[c.index()] for c in d.cells(f)]
    if len(localCells) == 1:
        topology = "boundary"  # boundary facet
    elif len(localCells) == 2 and localCells[0] == localCells[1]:
        topology = "internal"  # internal facet
    elif len(localCells) == 2:
        topology = "interface"  # interface facet
    else:
        raise Exception("Facet has more than two cells")
    return (topology, localCells)


def cube_condition(cell, xmin=0.3, xmax=0.7):
    """
    Returns true when inside an inner cube region defined as:
    xmin <= x <= xmax, xmin <= y <= xmax, xmin <= z <= xmax
    """
    return (
        (xmin - d.DOLFIN_EPS < cell.midpoint().x() < xmax + d.DOLFIN_EPS)
        and (xmin - d.DOLFIN_EPS < cell.midpoint().y() < xmax + d.DOLFIN_EPS)
        and (xmin - d.DOLFIN_EPS < cell.midpoint().z() < xmax + d.DOLFIN_EPS)
    )


def create_cubes(N=16, condition=cube_condition):
    """
    Creates a mesh for use in examples that contains
    two distinct cube subvolumes with a shared interface surface.
    Cell markers:
    1 - Default subvolume (volume outside the inner cube)
    2 - Subvolume specified by condition function

    Facet markers:
    12 - Interface between subvolumes
    10 - Boundary of subvolume 1
    0  - Interior facets
    """
    # Create a mesh
    mesh = d.UnitCubeMesh(N, N, N)
    # Initialize mesh functions
    mf3 = d.MeshFunction("size_t", mesh, 3, 0)
    mf2 = d.MeshFunction("size_t", mesh, 2, 0)

    # Mark all cells that satisfy condition as 3, else 1
    for c in d.cells(mesh):
        mf3[c] = 2 if condition(c) else 1

    # Mark facets
    for f in d.faces(mesh):
        topology, cellIndices = facet_topology(f, mf3)
        if topology == "interface":
            mf2[f] = 12
        elif topology == "boundary":
            mf2[f] = int(cellIndices[0] * 10)
        else:
            mf2[f] = 0
    return (mesh, mf2, mf3)


def create_spheres(
    outerRad: float = 0.5,
    innerRad: float = 0.25,
    hEdge: float = 0,
    hInnerEdge: float = 0,
    interface_marker: int = 12,
    outer_marker: int = 10,
    inner_vol_tag: int = 2,
    outer_vol_tag: int = 1,
    comm: MPI.Comm = d.MPI.comm_world,
    verbose: bool = False,
) -> Tuple[d.Mesh, d.MeshFunction, d.MeshFunction]:
    """
    Calls create_ellipsoids() to make spherical mesh
    Args:
        outerRad: radius of the outer sphere
        innerRad: radius of the inner sphere
    All other arguments are the same as described for create_ellipsoids()
    """
    dmesh, mf2, mf3 = create_ellipsoids(
        (outerRad, outerRad, outerRad),
        (innerRad, innerRad, innerRad),
        hEdge,
        hInnerEdge,
        interface_marker,
        outer_marker,
        inner_vol_tag,
        outer_vol_tag,
        comm,
        verbose,
    )
    return (dmesh, mf2, mf3)


def create_ellipsoids(
    outerRad: Tuple[float, float, float],
    innerRad: Tuple[float, float, float],
    hEdge: float = 0,
    hInnerEdge: float = 0,
    interface_marker: int = 12,
    outer_marker: int = 10,
    inner_vol_tag: int = 2,
    outer_vol_tag: int = 1,
    comm: MPI.Comm = d.MPI.comm_world,
    verbose: bool = False,
) -> Tuple[d.Mesh, d.MeshFunction, d.MeshFunction]:
    """
    Creates a mesh for use in examples that contains
    two distinct ellipsoid subvolumes with a shared interface
    surface. If the radius of the inner ellipsoid is 0, mesh a
    single ellipsoid.

    Args:
        outerRad: The radius of the outer ellipsoid
        innerRad: The radius of the inner ellipsoid
        hEdge: maximum mesh size at the outer edge
        hInnerEdge: maximum mesh size at the edge
            of the inner ellipsoid
        interface_marker: The value to mark facets on the interface with
        outer_marker: The value to mark facets on the outer ellipsoid with
        inner_vol_tag: The value to mark the inner ellipsoidal volume with
        outer_vol_tag: The value to mark the outer ellipsoidal volume with
        comm: MPI communicator to create the mesh with
        verbose: If true print gmsh output, else skip
    Returns:
        Tuple (mesh, facet_marker, cell_marker)
    """
    import gmsh

    if np.any(np.isclose(outerRad, 0)):
        ValueError("One of the outer radii is equal to zero")
    if np.isclose(hEdge, 0):
        hEdge = 0.1 * max(outerRad)
    if np.isclose(hInnerEdge, 0):
        hInnerEdge = 0.2 * max(outerRad) if np.any(np.isclose(innerRad, 0)) else 0.2 * max(innerRad)
    if innerRad[0] > outerRad[0] or innerRad[1] > outerRad[1] or innerRad[2] > outerRad[2]:
        ValueError("Inner ellipsoid does not fit inside outer ellipsoid")
    # Create the two ellipsoid mesh using gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", int(verbose))

    gmsh.model.add("twoellipsoids")
    # first add ellipsoid 1 of radius outerRad and center (0,0,0)
    outer_ellipsoid = gmsh.model.occ.addSphere(0, 0, 0, 1.0)
    gmsh.model.occ.dilate([(3, outer_ellipsoid)], 0, 0, 0, outerRad[0], outerRad[1], outerRad[2])
    if np.any(np.isclose(innerRad, 0)):
        # Use outer_ellipsoid only
        gmsh.model.occ.synchronize()
        gmsh.model.add_physical_group(3, [outer_ellipsoid], tag=outer_vol_tag)
        facets = gmsh.model.getBoundary([(3, outer_ellipsoid)])
        assert len(facets) == 1
        gmsh.model.add_physical_group(2, [facets[0][1]], tag=outer_marker)
    else:
        # Add inner_ellipsoid (radius innerRad, center (0,0,0))
        inner_ellipsoid = gmsh.model.occ.addSphere(0, 0, 0, 1.0)
        gmsh.model.occ.dilate(
            [(3, inner_ellipsoid)], 0, 0, 0, innerRad[0], innerRad[1], innerRad[2]
        )
        # Create interface between ellipsoids
        two_ellipsoids, (outer_ellipsoid_map, inner_ellipsoid_map) = gmsh.model.occ.fragment(
            [(3, outer_ellipsoid)], [(3, inner_ellipsoid)]
        )
        gmsh.model.occ.synchronize()

        # Get the outer boundary
        outer_shell = gmsh.model.getBoundary(two_ellipsoids, oriented=False)
        assert len(outer_shell) == 1
        # Get the inner boundary
        inner_shell = gmsh.model.getBoundary(inner_ellipsoid_map, oriented=False)
        assert len(inner_shell) == 1
        # Add physical markers for facets
        gmsh.model.add_physical_group(outer_shell[0][0], [outer_shell[0][1]], tag=outer_marker)
        gmsh.model.add_physical_group(inner_shell[0][0], [inner_shell[0][1]], tag=interface_marker)

        # Physical markers for
        all_volumes = [tag[1] for tag in outer_ellipsoid_map]
        inner_volume = [tag[1] for tag in inner_ellipsoid_map]
        outer_volume = []
        for vol in all_volumes:
            if vol not in inner_volume:
                outer_volume.append(vol)
        gmsh.model.add_physical_group(3, outer_volume, tag=outer_vol_tag)
        gmsh.model.add_physical_group(3, inner_volume, tag=inner_vol_tag)

    def meshSizeCallback(dim, tag, x, y, z, lc):
        # mesh length is hEdge at the PM (defaults to 0.1*outerRad,
        # or set when calling function) and hInnerEdge at the ERM
        # (defaults to 0.2*innerRad, or set when calling function)
        # between these, the value is interpolated based on R,
        # and inside the value is interpolated between hInnerEdge and 0.2*innerRad
        # If hInnerEdge > 0.2*innerRad, lc = hInnerRad inside the inner ellipsoid
        # if innerRad=0, then the mesh length is interpolated between
        # hEdge at the PM and 0.2*outerRad in the center
        R_rel_outer = np.sqrt(
            (x / outerRad[0]) ** 2 + (y / outerRad[1]) ** 2 + (z / outerRad[2]) ** 2
        )
        if np.any(np.isclose(innerRad, 0)):
            lc3 = 0.2 * max(outerRad)
            innerRad_scale = 0
            in_outer = True
        else:
            R_rel_inner = np.sqrt(
                (x / innerRad[0]) ** 2 + (y / innerRad[1]) ** 2 + (z / innerRad[2]) ** 2
            )
            lc3 = max(hInnerEdge, 0.2 * max(innerRad))
            innerRad_scale = np.mean(
                [innerRad[0] / outerRad[0], innerRad[1] / outerRad[1], innerRad[2] / outerRad[2]]
            )
            in_outer = R_rel_inner > 1
        lc1 = hEdge
        lc2 = hInnerEdge
        if in_outer:
            lcTest = lc1 + (lc2 - lc1) * (1 - R_rel_outer) / (1 - innerRad_scale)
        else:
            lcTest = lc2 + (lc3 - lc2) * (1 - R_rel_inner)
        return lcTest

    gmsh.model.mesh.setSizeCallback(meshSizeCallback)
    # set off the other options for mesh size determination
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    # this changes the algorithm from Frontal-Delaunay to Delaunay,
    # which may provide better results when there are larger gradients in mesh size
    gmsh.option.setNumber("Mesh.Algorithm", 5)

    gmsh.model.mesh.generate(3)
    rank = MPI.COMM_WORLD.rank
    tmp_folder = pathlib.Path(f"tmp_ellipsoid_{outerRad}_{innerRad}_{rank}")
    tmp_folder.mkdir(exist_ok=True)
    gmsh_file = tmp_folder / "ellipsoids.msh"
    gmsh.write(str(gmsh_file))
    gmsh.finalize()

    # return dolfin mesh of max dimension (parent mesh) and marker functions mf2 and mf3
    dmesh, mf2, mf3 = gmsh_to_dolfin(str(gmsh_file), tmp_folder, 3, comm)
    # remove tmp mesh and tmp folder
    gmsh_file.unlink(missing_ok=False)
    tmp_folder.rmdir()
    # return dolfin mesh, mf2 (2d tags) and mf3 (3d tags)
    return (dmesh, mf2, mf3)


def create_axisymm(
    outerExpr: str = "",
    innerExpr: str = "",
    hEdge: float = 0,
    hInnerEdge: float = 0,
    interface_marker: int = 12,
    outer_marker: int = 10,
    inner_vol_tag: int = 2,
    outer_vol_tag: int = 1,
    comm: MPI.Comm = d.MPI.comm_world,
    verbose: bool = False,
) -> Tuple[d.Mesh, d.MeshFunction, d.MeshFunction]:
    """
    Creates an axisymmetric mesh, with the bounding curve defined in
    terms of r and z. (e.g. unit circle defined by "r**2 + (z-1)**2 == 1")
    It is assumed that substrate is present at z = 0, so if the curve extends
    below z = 0 , there is a sharp cutoff.
    Can include one compartment inside another compartment

    Args:
        outerExpr: String implicitly defining an r-z curve for the outer surface
        innerExpr: String implicitly defining an r-z curve for the inner surface
        hEdge: maximum mesh size at the outer edge
        hInnerEdge: maximum mesh size at the edge
            of the inner compartment
        interface_marker: The value to mark facets on the interface with
        outer_marker: The value to mark facets on the outer ellipsoid with
        inner_vol_tag: The value to mark the inner ellipsoidal volume with
        outer_vol_tag: The value to mark the outer ellipsoidal volume with
        comm: MPI communicator to create the mesh with
        verbose: If true print gmsh output, else skip
    Returns:
        Tuple (mesh, facet_marker, cell_marker)
    """
    import gmsh

    if outerExpr == "":
        ValueError("Outer surface is not defined")

    rValsOuter, zValsOuter = implicit_axisymm(outerExpr)

    if not innerExpr == "":
        rValsInner, zValsInner = implicit_axisymm(innerExpr)
        zMid = np.mean(zValsInner)
        ROuterVec = np.sqrt(rValsOuter**2 + (zValsOuter - zMid) ** 2)
        RInnerVec = np.sqrt(rValsInner**2 + (zValsInner - zMid) ** 2)
        maxOuterDim = max(ROuterVec)
        maxInnerDim = max(RInnerVec)
    else:
        zMid = np.mean(zValsOuter)
        ROuterVec = np.sqrt(rValsOuter**2 + (zValsOuter - zMid) ** 2)
        maxOuterDim = max(ROuterVec)
    if np.isclose(hEdge, 0):
        hEdge = 0.1 * maxOuterDim
    if np.isclose(hInnerEdge, 0):
        hInnerEdge = 0.2 * maxOuterDim if innerExpr == "" else 0.2 * maxInnerDim
    # Create the two axisymmetric body mesh using gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", int(verbose))
    gmsh.model.add("axisymm")
    # first add outer body and revolve
    outer_tag_list = []
    for i in range(len(rValsOuter)):
        cur_tag = gmsh.model.occ.add_point(rValsOuter[i], 0, zValsOuter[i])
        outer_tag_list.append(cur_tag)
    outer_spline_tag = gmsh.model.occ.add_spline(outer_tag_list)
    if np.isclose(zValsOuter[-1], 0):  # then include substrate at z=0
        origin_tag = gmsh.model.occ.add_point(0, 0, 0)
        symm_axis_tag = gmsh.model.occ.add_line(origin_tag, outer_tag_list[0])
        bottom_tag = gmsh.model.occ.add_line(origin_tag, outer_tag_list[-1])
        outer_loop_tag = gmsh.model.occ.add_curve_loop(
            [outer_spline_tag, symm_axis_tag, bottom_tag]
        )
    else:
        symm_axis_tag = gmsh.model.occ.add_line(outer_tag_list[0], outer_tag_list[-1])
        outer_loop_tag = gmsh.model.occ.add_curve_loop([outer_spline_tag, symm_axis_tag])
    cell_plane_tag = gmsh.model.occ.add_plane_surface([outer_loop_tag])
    outer_shape = gmsh.model.occ.revolve([(2, cell_plane_tag)], 0, 0, 0, 0, 0, 1, 2 * np.pi)
    outer_shape_tags = []
    for i in range(len(outer_shape)):
        if outer_shape[i][0] == 3:  # pull out tags associated with 3d objects
            outer_shape_tags.append(outer_shape[i][1])
    assert len(outer_shape_tags) == 1  # should be just one 3D body from the full revolution

    if innerExpr == "":
        # No inner shape in this case
        gmsh.model.occ.synchronize()
        gmsh.model.add_physical_group(3, outer_shape_tags, tag=outer_vol_tag)
        facets = gmsh.model.getBoundary([(3, outer_shape_tags[0])])
        assert (
            len(facets) == 2
        )  # 2 boundaries because of bottom surface at z = 0, both belong to PM
        gmsh.model.add_physical_group(2, [facets[0][1], facets[1][1]], tag=outer_marker)
    else:
        # Add inner shape
        inner_tag_list = []
        for i in range(len(rValsInner)):
            cur_tag = gmsh.model.occ.add_point(rValsInner[i], 0, zValsInner[i])
            inner_tag_list.append(cur_tag)
        inner_spline_tag = gmsh.model.occ.add_spline(inner_tag_list)
        symm_inner_tag = gmsh.model.occ.add_line(inner_tag_list[0], inner_tag_list[-1])
        inner_loop_tag = gmsh.model.occ.add_curve_loop([inner_spline_tag, symm_inner_tag])
        inner_plane_tag = gmsh.model.occ.add_plane_surface([inner_loop_tag])
        inner_shape = gmsh.model.occ.revolve([(2, inner_plane_tag)], 0, 0, 0, 0, 0, 1, 2 * np.pi)
        inner_shape_tags = []
        for i in range(len(inner_shape)):
            if inner_shape[i][0] == 3:  # pull out tags associated with 3d objects
                inner_shape_tags.append(inner_shape[i][1])
        assert len(inner_shape_tags) == 1  # should be just one 3D body from the full revolution

        # Create interface between 2 objects
        two_shapes, (outer_shape_map, inner_shape_map) = gmsh.model.occ.fragment(
            [(3, outer_shape_tags[0])], [(3, inner_shape_tags[0])]
        )
        gmsh.model.occ.synchronize()

        # Get the outer boundary
        outer_shell = gmsh.model.getBoundary(two_shapes, oriented=False)
        assert (
            len(outer_shell) == 2
        )  # 2 boundaries because of bottom surface at z = 0, both belong to PM
        # Get the inner boundary
        inner_shell = gmsh.model.getBoundary(inner_shape_map, oriented=False)
        assert len(inner_shell) == 1
        # Add physical markers for facets
        gmsh.model.add_physical_group(
            outer_shell[0][0], [outer_shell[0][1], outer_shell[1][1]], tag=outer_marker
        )
        gmsh.model.add_physical_group(inner_shell[0][0], [inner_shell[0][1]], tag=interface_marker)

        # Physical markers for
        all_volumes = [tag[1] for tag in outer_shape_map]
        inner_volume = [tag[1] for tag in inner_shape_map]
        outer_volume = []
        for vol in all_volumes:
            if vol not in inner_volume:
                outer_volume.append(vol)
        gmsh.model.add_physical_group(3, outer_volume, tag=outer_vol_tag)
        gmsh.model.add_physical_group(3, inner_volume, tag=inner_vol_tag)

    def meshSizeCallback(dim, tag, x, y, z, lc):
        # mesh length is hEdge at the PM and hInnerEdge at the inner membrane
        # between these, the value is interpolated based on the relative distance
        # between the two membranes.
        # Inside the inner shape, the value is interpolated between hInnerEdge
        # and lc3, where lc3 = max(hInnerEdge, 0.2*maxInnerDim)
        # if innerRad=0, then the mesh length is interpolated between
        # hEdge at the PM and 0.2*maxOuterDim in the center
        rCur = np.sqrt(x**2 + y**2)
        RCur = np.sqrt(rCur**2 + (z - zMid) ** 2)
        outer_dist = np.sqrt((rCur - rValsOuter) ** 2 + (z - zValsOuter) ** 2)
        np.append(outer_dist, z)  # include the distance from the substrate
        dist_to_outer = min(outer_dist)
        if innerExpr == "":
            lc3 = 0.2 * maxOuterDim
            dist_to_inner = RCur
            in_outer = True
        else:
            inner_dist = np.sqrt((rCur - rValsInner) ** 2 + (z - zValsInner) ** 2)
            dist_to_inner = min(inner_dist)
            inner_idx = np.argmin(inner_dist)
            inner_rad = RInnerVec[inner_idx]
            R_rel_inner = RCur / inner_rad
            lc3 = max(hInnerEdge, 0.2 * maxInnerDim)
            in_outer = R_rel_inner > 1
        lc1 = hEdge
        lc2 = hInnerEdge
        if in_outer:
            lcTest = lc1 + (lc2 - lc1) * (dist_to_outer) / (dist_to_inner + dist_to_outer)
        else:
            lcTest = lc2 + (lc3 - lc2) * (1 - R_rel_inner)
        return lcTest

    gmsh.model.mesh.setSizeCallback(meshSizeCallback)
    # set off the other options for mesh size determination
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    # this changes the algorithm from Frontal-Delaunay to Delaunay,
    # which may provide better results when there are larger gradients in mesh size
    gmsh.option.setNumber("Mesh.Algorithm", 5)

    gmsh.model.mesh.generate(3)
    rank = MPI.COMM_WORLD.rank
    tmp_folder = pathlib.Path(f"tmp_axisymm_{rank}")
    tmp_folder.mkdir(exist_ok=True)
    gmsh_file = tmp_folder / "axisymm.msh"
    gmsh.write(str(gmsh_file))
    gmsh.finalize()

    # return dolfin mesh of max dimension (parent mesh) and marker functions mf2 and mf3
    dmesh, mf2, mf3 = gmsh_to_dolfin(str(gmsh_file), tmp_folder, 3, comm)
    # remove tmp mesh and tmp folder
    gmsh_file.unlink(missing_ok=False)
    tmp_folder.rmdir()
    # return dolfin mesh, mf2 (2d tags) and mf3 (3d tags)
    return (dmesh, mf2, mf3)


def create_cylinders(
    outerRad: float = 1.0,
    innerRad: float = 0.0,
    outerLength: float = 10.0,
    innerLength: float = 8.0,
    hEdge: float = 0,
    hInnerEdge: float = 0,
    interface_marker: int = 12,
    outer_marker: int = 10,
    inner_vol_tag: int = 2,
    outer_vol_tag: int = 1,
    comm: MPI.Comm = d.MPI.comm_world,
    verbose: bool = False,
) -> Tuple[d.Mesh, d.MeshFunction, d.MeshFunction]:
    """
    Creates a mesh for use in examples that contains
    two distinct ellipsoid subvolumes with a shared interface
    surface. If the radius of the inner ellipsoid is 0, mesh a
    single ellipsoid.

    Args:
        outerRad: The radius of the outer cylinder
        innerRad: The radius of the inner cylinder
        outerLength: length of the outer cylinder
        innerLength: length of the inner cylinder
        hEdge: maximum mesh size at the outer edge
        hInnerEdge: maximum mesh size at the edge
            of the inner cylinder
        interface_marker: The value to mark facets on the interface with
        outer_marker: The value to mark facets on the outer ellipsoid with
        inner_vol_tag: The value to mark the inner spherical volume with
        outer_vol_tag: The value to mark the outer spherical volume with
        comm: MPI communicator to create the mesh with
        verbose: If true print gmsh output, else skip
    Returns:
        A triplet (mesh, facet_marker, cell_marker)
    """
    import gmsh

    if np.isclose(outerRad, 0):
        ValueError("Outer radius is equal to zero")
    if np.isclose(hEdge, 0):
        hEdge = 0.1 * max(outerRad)
    if np.isclose(hInnerEdge, 0):
        hInnerEdge = 0.2 * outerRad if np.isclose(innerRad, 0) else 0.2 * innerRad
    if innerRad > outerRad or innerLength >= outerLength:
        ValueError("Inner cylinder does not fit inside outer cylinder")
    # Create the two cylinder mesh using gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", int(verbose))

    gmsh.model.add("twocylinders")
    # first add cylinder 1 of radius outerRad and center (0,0,0)
    outer_cylinder = gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, outerLength, outerRad)
    if np.isclose(innerRad, 0):
        # Use outer_cylinder only
        gmsh.model.occ.synchronize()
        gmsh.model.add_physical_group(3, [outer_cylinder], tag=outer_vol_tag)
        facets = gmsh.model.getBoundary([(3, outer_cylinder)])
        gmsh.model.add_physical_group(2, [facets[0][1]], tag=outer_marker)
    else:
        # Add inner_cylinder (radius innerRad,
        # center (0,0,(outerLength-innerLength)/2))
        inner_cylinder = gmsh.model.occ.addCylinder(
            0, 0, (outerLength - innerLength) / 2, 0, 0, innerLength, innerRad
        )
        # Create interface between cylinders
        two_cylinders, (outer_cylinder_map, inner_cylinder_map) = gmsh.model.occ.fragment(
            [(3, outer_cylinder)], [(3, inner_cylinder)]
        )
        gmsh.model.occ.synchronize()

        # Get the outer boundary
        outer_shell = gmsh.model.getBoundary(two_cylinders, oriented=False)
        # Get the inner boundary
        inner_shell = gmsh.model.getBoundary(inner_cylinder_map, oriented=False)
        # Add physical markers for facets
        gmsh.model.add_physical_group(outer_shell[0][0], [outer_shell[0][1]], tag=outer_marker)
        gmsh.model.add_physical_group(inner_shell[0][0], [inner_shell[0][1]], tag=interface_marker)

        # Physical markers for
        all_volumes = [tag[1] for tag in outer_cylinder_map]
        inner_volume = [tag[1] for tag in inner_cylinder_map]
        outer_volume = []
        for vol in all_volumes:
            if vol not in inner_volume:
                outer_volume.append(vol)
        gmsh.model.add_physical_group(3, outer_volume, tag=outer_vol_tag)
        gmsh.model.add_physical_group(3, inner_volume, tag=inner_vol_tag)

    def meshSizeCallback(dim, tag, x, y, z, lc):
        # mesh length is hEdge at the PM (defaults to 0.1*outerRad,
        # or set when calling function) and hInnerEdge at the ERM
        # (defaults to 0.2*innerRad, or set when calling function)
        # between these, the value is interpolated based on r (polar coord),
        # and inside the value is interpolated between hInnerEdge and 0.2*innerRad
        # if innerRad=0, then the mesh length is interpolated between
        # hEdge at the PM and 0.2*outerRad in the center
        r_cur = np.sqrt(x**2 + y**2)
        if np.isclose(innerRad, 0):
            lc3 = 0.2 * outerRad
        else:
            lc3 = max(hInnerEdge, 0.2 * innerRad)
        lc1 = hEdge
        lc2 = hInnerEdge
        if r_cur > innerRad:
            lcTest = lc1 + (lc2 - lc1) * (outerRad - r_cur) / (outerRad - innerRad)
        else:
            lcTest = lc2 + (lc3 - lc2) * (innerRad - r_cur) / innerRad
        return lcTest

    gmsh.model.mesh.setSizeCallback(meshSizeCallback)
    # set off the other options for mesh size determination
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    # this changes the algorithm from Frontal-Delaunay to Delaunay,
    # which may provide better results when there are larger gradients in mesh size
    gmsh.option.setNumber("Mesh.Algorithm", 5)

    gmsh.model.mesh.generate(3)
    rank = MPI.COMM_WORLD.rank
    tmp_folder = pathlib.Path(f"tmp_cylinder_{outerRad}_{innerRad}_{rank}")
    tmp_folder.mkdir(exist_ok=True)
    gmsh_file = tmp_folder / "cylinders.msh"
    gmsh.write(str(gmsh_file))
    gmsh.finalize()

    # return dolfin mesh of max dimension (parent mesh) and marker functions mf2 and mf3
    dmesh, mf2, mf3 = gmsh_to_dolfin(str(gmsh_file), tmp_folder, 3, comm)
    # remove tmp mesh and tmp folder
    gmsh_file.unlink(missing_ok=False)
    tmp_folder.rmdir()
    # return dolfin mesh, mf2 (2d tags) and mf3 (3d tags)
    return (dmesh, mf2, mf3)


def create_ellipses(
    xrad_outer: float = 3.0,
    yrad_outer: float = 1.0,
    xrad_inner: float = 0.0,
    yrad_inner: float = 0.0,
    hEdge: float = 0.1,
    hInnerEdge: float = 0.1,
    interface_marker: int = 12,
    outer_marker: int = 10,
    inner_tag: int = 2,
    outer_tag: int = 1,
    comm: MPI.Comm = d.MPI.comm_world,
    verbose: bool = True,
) -> Tuple[d.Mesh, d.MeshFunction, d.MeshFunction]:
    """
    Creates a mesh for an ellipse surface,
    optionally includes an ellipse within the main ellipse
    Args:
        xrad_outer: outer radius assoc with x axis
        yrad_outer: outer radius assoc with y axis
        xrad_inner: x radius of inner ellipse (optional)
        yrad_inner: y radius of inner ellipse (optional)
        hEdge: mesh resolution at outer edge
        hInnerEdge: mesh resolution at edge of inner ellipse
        interface_marker: The value to mark facets on the interface with
        outer_marker: The value to mark facets on edge of the outer ellipse with
        inner_tag: The value to mark the inner ellipse surface with
        outer_tag: The value to mark the outer ellipse surface with
        comm: MPI communicator to create the mesh with
        verbose: If true print gmsh output, else skip
    Returns:
        Tuple (mesh, facet_marker (mf1), cell_marker(mf2))
    """
    import gmsh

    outerRad = [xrad_outer, yrad_outer]
    innerRad = [xrad_inner, yrad_inner]
    if np.any(np.isclose(outerRad, 0)):
        ValueError("One of the outer radii is equal to zero")
    if np.isclose(hEdge, 0):
        hEdge = 0.1 * max(outerRad)
    if np.isclose(hInnerEdge, 0):
        hInnerEdge = 0.2 * max(outerRad) if np.any(np.isclose(innerRad, 0)) else 0.2 * max(innerRad)
    if innerRad[0] > outerRad[0] or innerRad[1] > outerRad[1]:
        ValueError("Inner ellipse does not fit inside outer ellipse")
    # Create the two ellipse mesh using gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", int(verbose))

    gmsh.model.add("ellipses")
    # first add ellipse 1 of radius outerRad and center (0,0,0)
    outer_ellipse = gmsh.model.occ.addDisk(0, 0, 0, xrad_outer, yrad_outer)
    if np.any(np.isclose(innerRad, 0)):
        # Use outer_ellipse only
        gmsh.model.occ.synchronize()
        gmsh.model.add_physical_group(2, [outer_ellipse], tag=outer_tag)
        facets = gmsh.model.getBoundary([(2, outer_ellipse)])
        assert len(facets) == 1
        gmsh.model.add_physical_group(1, [facets[0][1]], tag=outer_marker)
    else:
        # Add inner_ellipse (radius innerRad, center (0,0,0))
        inner_ellipse = gmsh.model.occ.addDisk(0, 0, 0, xrad_inner, yrad_inner)
        # Create interface between ellipses
        two_ellipses, (outer_ellipse_map, inner_ellipse_map) = gmsh.model.occ.fragment(
            [(2, outer_ellipse)], [(2, inner_ellipse)]
        )
        gmsh.model.occ.synchronize()

        # Get the outer boundary
        outer_shell = gmsh.model.getBoundary(two_ellipses, oriented=False)
        assert len(outer_shell) == 1
        # Get the inner boundary
        inner_shell = gmsh.model.getBoundary(inner_ellipse_map, oriented=False)
        assert len(inner_shell) == 1
        # Add physical markers for facets
        gmsh.model.add_physical_group(outer_shell[0][0], [outer_shell[0][1]], tag=outer_marker)
        gmsh.model.add_physical_group(inner_shell[0][0], [inner_shell[0][1]], tag=interface_marker)

        # Physical markers for
        all_surfs = [tag[1] for tag in outer_ellipse_map]
        inner_surf = [tag[1] for tag in inner_ellipse_map]
        outer_surf = []
        for surf in all_surfs:
            if surf not in inner_surf:
                outer_surf.append(surf)
        gmsh.model.add_physical_group(2, outer_surf, tag=outer_tag)
        gmsh.model.add_physical_group(2, inner_surf, tag=inner_tag)

    def meshSizeCallback(dim, tag, x, y, z, lc):
        # mesh length is hEdge at the PM (defaults to 0.1*outerRad,
        # or set when calling function) and hInnerEdge at the ERM
        # (defaults to 0.2*innerRad, or set when calling function)
        # between these, the value is interpolated based on R,
        # and inside the value is interpolated between hInnerEdge and 0.2*innerRad
        # If hInnerEdge > 0.2*innerRad, lc = hInnerEdge inside the inner ellipse
        # if innerRad=0, then the mesh length is interpolated between
        # hEdge at the PM and 0.2*outerRad in the center
        R_rel_outer = np.sqrt((x / outerRad[0]) ** 2 + (y / outerRad[1]) ** 2)
        if np.any(np.isclose(innerRad, 0)):
            lc3 = 0.2 * max(outerRad)
            innerRad_scale = 0
            in_outer = True
        else:
            R_rel_inner = np.sqrt((x / innerRad[0]) ** 2 + (y / innerRad[1]) ** 2)
            lc3 = max(hInnerEdge, 0.2 * max(innerRad))
            innerRad_scale = np.mean([innerRad[0] / outerRad[0], innerRad[1] / outerRad[1]])
            in_outer = R_rel_inner > 1
        lc1 = hEdge
        lc2 = hInnerEdge
        if in_outer:
            lcTest = lc1 + (lc2 - lc1) * (1 - R_rel_outer) / (1 - innerRad_scale)
        else:
            lcTest = lc2 + (lc3 - lc2) * (1 - R_rel_inner)
        return lcTest

    gmsh.model.mesh.setSizeCallback(meshSizeCallback)
    # set off the other options for mesh size determination
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    # this changes the algorithm from Frontal-Delaunay to Delaunay,
    # which may provide better results when there are larger gradients in mesh size
    gmsh.option.setNumber("Mesh.Algorithm", 5)

    gmsh.model.mesh.generate(2)
    rank = MPI.COMM_WORLD.rank
    tmp_folder = pathlib.Path(f"tmp_ellipse_{outerRad}_{innerRad}_{rank}")
    tmp_folder.mkdir(exist_ok=True)
    gmsh_file = tmp_folder / "ellipses.msh"
    gmsh.write(str(gmsh_file))
    gmsh.finalize()

    # return dolfin mesh of max dimension (parent mesh) and marker functions mf2 and mf3
    dmesh, mf1, mf2 = gmsh_to_dolfin(str(gmsh_file), tmp_folder, 2, comm)
    # remove tmp mesh and tmp folder
    gmsh_file.unlink(missing_ok=False)
    tmp_folder.rmdir()
    # return dolfin mesh, mf1 (1d tags) and mf2 (2d tags)
    return (dmesh, mf1, mf2)


def create_2Dcell(
    outerExpr: str = "",
    innerExpr: str = "",
    hEdge: float = 0,
    hInnerEdge: float = 0,
    interface_marker: int = 12,
    outer_marker: int = 10,
    inner_tag: int = 2,
    outer_tag: int = 1,
    comm: MPI.Comm = d.MPI.comm_world,
    verbose: bool = False,
    half_cell: bool = True,
) -> Tuple[d.Mesh, d.MeshFunction, d.MeshFunction]:
    """
    Creates a 2D mesh of a cell profile, with the bounding curve defined in
    terms of r and z (e.g. unit circle would be "r**2 + (z-1)**2 == 1)
    It is assumed that substrate is present at z = 0, so if the curve extends
    below z = 0 , there is a sharp cutoff.
    If half_cell = True, only have of the contour is constructed, with a
    left zero-flux boundary at r = 0.
    Can include one compartment inside another compartment.
    Recommended for use with the axisymmetric feature of SMART.

    Args:
        outerExpr: String implicitly defining an r-z curve for the outer surface
        innerExpr: String implicitly defining an r-z curve for the inner surface
        hEdge: maximum mesh size at the outer edge
        hInnerEdge: maximum mesh size at the edge
            of the inner compartment
        interface_marker: The value to mark facets on the interface with
        outer_marker: The value to mark facets on edge of the outer ellipse with
        inner_tag: The value to mark the inner ellipse surface with
        outer_tag: The value to mark the outer ellipse surface with
        comm: MPI communicator to create the mesh with
        verbose: If true print gmsh output, else skip
        half_cell: If true, consider r=0 the symmetry axis for an axisymm shape
    Returns:
        Tuple (mesh, facet_marker, cell_marker)
    """
    import gmsh

    if outerExpr == "":
        ValueError("Outer surface is not defined")

    rValsOuter, zValsOuter = implicit_axisymm(outerExpr)

    if not innerExpr == "":
        rValsInner, zValsInner = implicit_axisymm(innerExpr)
        zMid = np.mean(zValsInner)
        ROuterVec = np.sqrt(rValsOuter**2 + (zValsOuter - zMid) ** 2)
        RInnerVec = np.sqrt(rValsInner**2 + (zValsInner - zMid) ** 2)
        maxOuterDim = max(ROuterVec)
        maxInnerDim = max(RInnerVec)
    else:
        zMid = np.mean(zValsOuter)
        ROuterVec = np.sqrt(rValsOuter**2 + (zValsOuter - zMid) ** 2)
        maxOuterDim = max(ROuterVec)
    if np.isclose(hEdge, 0):
        hEdge = 0.1 * maxOuterDim
    if np.isclose(hInnerEdge, 0):
        hInnerEdge = 0.2 * maxOuterDim if innerExpr == "" else 0.2 * maxInnerDim
    # Create the 2D mesh using gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", int(verbose))
    gmsh.model.add("2DCell")
    # first add outer body and revolve
    outer_tag_list = []
    for i in range(len(rValsOuter)):
        cur_tag = gmsh.model.occ.add_point(rValsOuter[i], 0, zValsOuter[i])
        outer_tag_list.append(cur_tag)
    outer_spline_tag = gmsh.model.occ.add_spline(outer_tag_list)
    if np.isclose(zValsOuter[-1], 0):  # then include substrate at z=0
        if half_cell:
            origin_tag = gmsh.model.occ.add_point(0, 0, 0)
            symm_axis_tag = gmsh.model.occ.add_line(origin_tag, outer_tag_list[0])
            bottom_tag = gmsh.model.occ.add_line(origin_tag, outer_tag_list[-1])
            outer_loop_tag = gmsh.model.occ.add_curve_loop(
                [outer_spline_tag, bottom_tag, symm_axis_tag]
            )
        else:
            bottom_tag = gmsh.model.occ.add_line(outer_tag_list[0], outer_tag_list[-1])
            outer_loop_tag = gmsh.model.occ.add_curve_loop([outer_spline_tag, bottom_tag])
    else:
        if half_cell:
            symm_axis_tag = gmsh.model.occ.add_line(outer_tag_list[0], outer_tag_list[-1])
            outer_loop_tag = gmsh.model.occ.add_curve_loop([outer_spline_tag, symm_axis_tag])
        else:
            outer_loop_tag = gmsh.model.occ.add_curve_loop([outer_spline_tag])
    cell_plane_tag = gmsh.model.occ.add_plane_surface([outer_loop_tag])

    if innerExpr == "":
        # No inner shape in this case
        gmsh.model.occ.synchronize()
        gmsh.model.add_physical_group(2, cell_plane_tag, tag=outer_tag)
        facets = gmsh.model.getBoundary([(2, cell_plane_tag)])
        facet_tag_list = []
        for i in range(len(facets)):
            facet_tag_list.append(facets[i][1])
        if half_cell:  # if half, set symmetry axis to 0 (no flux)
            rRef = max(rValsOuter)
            xmin, ymin, zmin = (-rRef / 10, -rRef / 10, -1)
            xmax, ymax, zmax = (rRef / 10, rRef / 10, max(zValsOuter) + 1)
            all_symm_bound = gmsh.model.occ.get_entities_in_bounding_box(
                xmin, ymin, zmin, xmax, ymax, zmax, dim=1
            )
            symm_bound_markers = []
            for i in range(len(all_symm_bound)):
                symm_bound_markers.append(all_symm_bound[i][1])
            gmsh.model.add_physical_group(1, symm_bound_markers, tag=0)
        gmsh.model.add_physical_group(1, facet_tag_list, tag=outer_marker)
    else:
        # Add inner shape
        inner_tag_list = []
        for i in range(len(rValsInner)):
            cur_tag = gmsh.model.occ.add_point(rValsInner[i], 0, zValsInner[i])
            inner_tag_list.append(cur_tag)
        inner_spline_tag = gmsh.model.occ.add_spline(inner_tag_list)
        if half_cell:
            symm_inner_tag = gmsh.model.occ.add_line(inner_tag_list[0], inner_tag_list[-1])
            inner_loop_tag = gmsh.model.occ.add_curve_loop([inner_spline_tag, symm_inner_tag])
        else:
            inner_loop_tag = gmsh.model.occ.add_curve_loop([inner_spline_tag])
        inner_plane_tag = gmsh.model.occ.add_plane_surface([inner_loop_tag])

        # Create interface between 2 objects
        two_shapes, (outer_shape_map, inner_shape_map) = gmsh.model.occ.fragment(
            [(2, cell_plane_tag)], [(2, inner_plane_tag)]
        )
        gmsh.model.occ.synchronize()

        # Get the outer boundary
        outer_shell = gmsh.model.getBoundary(two_shapes, oriented=False)
        outer_marker_list = []
        for i in range(len(outer_shell)):
            outer_marker_list.append(outer_shell[i][1])
        # Get the inner boundary
        inner_shell = gmsh.model.getBoundary(inner_shape_map, oriented=False)
        inner_marker_list = []
        for i in range(len(inner_shell)):
            inner_marker_list.append(inner_shell[i][1])
        # Add physical markers for facets
        if half_cell:  # if half, set symmetry axis to 0 (no flux)
            rRef = max(rValsInner)
            xmin, ymin, zmin = (-rRef / 10, -rRef / 10, -1)
            xmax, ymax, zmax = (rRef / 10, rRef / 10, max(zValsOuter) + 1)
            all_symm_bound = gmsh.model.occ.get_entities_in_bounding_box(
                xmin, ymin, zmin, xmax, ymax, zmax, dim=1
            )
            symm_bound_markers = []
            for i in range(len(all_symm_bound)):
                symm_bound_markers.append(all_symm_bound[i][1])
            gmsh.model.add_physical_group(1, symm_bound_markers, tag=0)
        gmsh.model.add_physical_group(1, outer_marker_list, tag=outer_marker)
        gmsh.model.add_physical_group(1, inner_marker_list, tag=interface_marker)

        # Physical markers for "volumes"
        all_volumes = [tag[1] for tag in outer_shape_map]
        inner_volume = [tag[1] for tag in inner_shape_map]
        outer_volume = []
        for vol in all_volumes:
            if vol not in inner_volume:
                outer_volume.append(vol)
        gmsh.model.add_physical_group(2, outer_volume, tag=outer_tag)
        gmsh.model.add_physical_group(2, inner_volume, tag=inner_tag)

    def meshSizeCallback(dim, tag, x, y, z, lc):
        # mesh length is hEdge at the PM and hInnerEdge at the inner membrane
        # between these, the value is interpolated based on the relative distance
        # between the two membranes.
        # Inside the inner shape, the value is interpolated between hInnerEdge
        # and lc3, where lc3 = max(hInnerEdge, 0.2*maxInnerDim)
        # if innerRad=0, then the mesh length is interpolated between
        # hEdge at the PM and 0.2*maxOuterDim in the center
        rCur = np.sqrt(x**2 + y**2)
        RCur = np.sqrt(rCur**2 + (z - zMid) ** 2)
        outer_dist = np.sqrt((rCur - rValsOuter) ** 2 + (z - zValsOuter) ** 2)
        np.append(outer_dist, z)  # include the distance from the substrate
        dist_to_outer = min(outer_dist)
        if innerExpr == "":
            lc3 = 0.2 * maxOuterDim
            dist_to_inner = RCur
            in_outer = True
        else:
            inner_dist = np.sqrt((rCur - rValsInner) ** 2 + (z - zValsInner) ** 2)
            dist_to_inner = min(inner_dist)
            inner_idx = np.argmin(inner_dist)
            inner_rad = RInnerVec[inner_idx]
            R_rel_inner = RCur / inner_rad
            lc3 = max(hInnerEdge, 0.2 * maxInnerDim)
            in_outer = R_rel_inner > 1
        lc1 = hEdge
        lc2 = hInnerEdge
        if in_outer:
            lcTest = lc1 + (lc2 - lc1) * (dist_to_outer) / (dist_to_inner + dist_to_outer)
        else:
            lcTest = lc2 + (lc3 - lc2) * (1 - R_rel_inner)
        return lcTest

    gmsh.model.mesh.setSizeCallback(meshSizeCallback)
    # set off the other options for mesh size determination
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    # this changes the algorithm from Frontal-Delaunay to Delaunay,
    # which may provide better results when there are larger gradients in mesh size
    gmsh.option.setNumber("Mesh.Algorithm", 5)

    gmsh.model.mesh.generate(2)
    rank = MPI.COMM_WORLD.rank
    tmp_folder = pathlib.Path(f"tmp_2DCell_{rank}")
    tmp_folder.mkdir(exist_ok=True)
    gmsh_file = tmp_folder / "2DCell.msh"
    gmsh.write(str(gmsh_file))
    gmsh.finalize()

    # return dolfin mesh of max dimension (parent mesh) and marker functions mf2 and mf3
    dmesh, mf2, mf3 = gmsh_to_dolfin(str(gmsh_file), tmp_folder, 2, comm)
    # remove tmp mesh and tmp folder
    gmsh_file.unlink(missing_ok=False)
    tmp_folder.rmdir()
    # return dolfin mesh, mf2 (2d tags) and mf3 (3d tags)
    return (dmesh, mf2, mf3)


def gmsh_to_dolfin(
    gmsh_file_name: str,
    tmp_folder: pathlib.Path = pathlib.Path("tmp_folder"),
    dimension: int = 3,
    comm: MPI.Comm = d.MPI.comm_world,
) -> Tuple[d.Mesh, d.MeshFunction, d.MeshFunction]:
    """
    Convert .msh file from gmsh to dolfin mesh
    and associated marker files (using meshio).
    Markers are assigned from gmsh mesh, any unassigned
    marker values are given value 0.
    Args:
        gmsh_file_name: .msh file (string)
        tmp_folder_name: folder name to store temporary mesh files
        dimension: dimension of parent mesh (int - either 2 or 3)
    Returns:
        Tuple containing:
            dMesh: Dolfin-style parent mesh
            mf_facet: markers for facets
            mf_cell: markers for cells
    """
    import meshio

    # load, convert to xdmf, and save as temp files
    mesh_in = meshio.read(gmsh_file_name)
    if dimension == 2:
        cell_type = "triangle"
        facet_type = "line"
    elif dimension == 3:
        cell_type = "tetra"
        facet_type = "triangle"
    else:
        ValueError(f"Mesh of dimension {dimension} not implemented")
    # convert cell mesh
    cells = mesh_in.get_cells_type(cell_type)
    cell_data = mesh_in.get_cell_data("gmsh:physical", cell_type)  # extract values of tags
    out_mesh_cell = meshio.Mesh(
        points=mesh_in.points,
        cells={cell_type: cells},
        cell_data={"mf_data": [cell_data]},
    )
    tmp_file_cell = tmp_folder / "tempmesh_cell.xdmf"
    meshio.write(tmp_file_cell, out_mesh_cell)
    # convert facet mesh
    facets = mesh_in.get_cells_type(facet_type)
    facet_data = mesh_in.get_cell_data("gmsh:physical", facet_type)  # extract values of tags
    out_mesh_facet = meshio.Mesh(
        points=mesh_in.points,
        cells={facet_type: facets},
        cell_data={"mf_data": [facet_data]},
    )
    tmp_file_facet = tmp_folder / "tempmesh_facet.xdmf"
    meshio.write(tmp_file_facet, out_mesh_facet)

    # convert xdmf mesh to dolfin-style mesh
    dmesh = d.Mesh(comm)
    mvc_cell = d.MeshValueCollection("size_t", dmesh, dimension)
    with d.XDMFFile(comm, str(tmp_file_cell)) as infile:
        infile.read(dmesh)
        infile.read(mvc_cell, "mf_data")
    mf_cell = d.cpp.mesh.MeshFunctionSizet(dmesh, mvc_cell)
    # set unassigned volumes to tag=0
    mf_cell.array()[np.where(mf_cell.array() > 1e9)[0]] = 0

    mvc_facet = d.MeshValueCollection("size_t", dmesh, dimension - 1)
    with d.XDMFFile(comm, str(tmp_file_facet)) as infile:
        infile.read(mvc_facet, "mf_data")
    mf_facet = d.cpp.mesh.MeshFunctionSizet(dmesh, mvc_facet)
    # set unassigned faces to tag=0
    mf_facet.array()[np.where(mf_facet.array() > 1e9)[0]] = 0

    # remove temp meshes
    tmp_file_cell.unlink(missing_ok=False)
    tmp_file_cell.with_suffix(".h5").unlink(missing_ok=False)
    tmp_file_facet.unlink(missing_ok=False)
    tmp_file_facet.with_suffix(".h5").unlink(missing_ok=False)
    # return dolfin mesh and mfs (marker functions)
    return (dmesh, mf_facet, mf_cell)


def write_mesh(
    mesh: d.Mesh,
    mf_facet: d.MeshFunction,
    mf_cell: d.MeshFunction,
    filename: pathlib.Path = pathlib.Path("DemoMesh.h5"),
):
    """
    Write 3D mesh, with cell markers (mf_cell)
    and facet markers (mf_facet) to hdf5 file and pvd files.
    """
    if isinstance(filename, str):
        filename = pathlib.Path(filename)
    comm = mesh.mpi_comm()
    # extract dimensionality for meshfunctions
    cell_dim = mf_cell.dim()
    facet_dim = mf_facet.dim()
    # Write mesh and meshfunctions to file
    hdf5 = d.HDF5File(comm, str(filename.with_suffix(".h5")), "w")
    hdf5.write(mesh, "/mesh")
    hdf5.write(mf_cell, f"/mf{cell_dim}")
    hdf5.write(mf_facet, f"/mf{facet_dim}")
    # For visualization of domains
    (
        d.File(
            mesh.mpi_comm(),
            str(filename.with_stem(filename.stem + f"_mf{cell_dim}").with_suffix(".pvd")),
        )
        << mf_cell
    )
    (
        d.File(
            mesh.mpi_comm(),
            str(filename.with_stem(filename.stem + f"_mf{facet_dim}").with_suffix(".pvd")),
        )
        << mf_facet
    )
