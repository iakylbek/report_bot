from .employee import employee_router
from .entering_data import entering_data_router
from .product import product_router
from .operation import operation_router
from .start import start_router
from .remains import remains_router
from .operation_report import report_router
from .export import export_router


__all__ = [
    "start_router",
    "entering_data_router",
    "employee_router",
    "product_router",
    "operation_router",
    "remains_router",
    "report_router",
    "export_router",
]
