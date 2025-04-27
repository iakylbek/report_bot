from .start import start_router
from .remains import remains_router
from .total_remains import total_remains_router
from .specific_remains import specific_remains_router
from .receipt import receipt_router
from .total_receipt import total_receipt_router
from .specific_receipt import specific_receipt_router
from .shipment import shipment_router
from .total_shipment import total_shipment_router
from .specific_shipment import specific_shipment_router
from .actions.employy import employy_router
from .actions.product import product_router
from .actions.operation import operation_router

__all__ = [
    "start_router",

    "remains_router",
    "total_remains_router",
    "specific_remains_router",

    "receipt_router",
    "total_receipt_router",
    "specific_receipt_router",

    "shipment_router",
    "total_shipment_router",
    'specific_shipment_router',

    "employy_router",
    "product_router",
    "operation_router",
]
