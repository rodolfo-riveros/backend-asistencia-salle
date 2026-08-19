from app.schemas.programas  import ProgramaCreate, ProgramaUpdate, ProgramaOut
from app.schemas.unidades   import (
    UnidadCreate, UnidadUpdate, UnidadOut, UnidadConPrograma, SemestreEnum
)
from app.schemas.docentes   import DocenteCreate, DocenteUpdate, DocenteOut
from app.schemas.alumnos    import (
    AlumnoCreate, AlumnoUpdate, AlumnoOut, AlumnoConPrograma, PromoverSalonRequest
)
from app.schemas.recuperaciones import (
    RecEstudianteCreate, RecEstudianteUpdate, RecEstudianteOut,
    RecMatriculaCreate, RecMatriculaOut,
    RecEvaluacionCreate, RecEvaluacionOut,
)
from app.schemas.asistencias import (
    AsignacionCreate, AsignacionUpdate, AsignacionOut, AsignacionDetalle,
    AsistenciaCreate, AsistenciaUpdate, AsistenciaOut, AsistenciaUpsert,
    AsistenciaDetalle, ResumenAsistencia, EstadoAsistencia,
)
