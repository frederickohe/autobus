"""Product Service"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import logging
import uuid
import re

from core.product.model.product import Product, Inventory
from core.product.dto.product_create_dto import ProductCreateDTO
from core.product.dto.product_update_dto import ProductUpdateDTO
from core.product.dto.inventory_create_dto import InventoryCreateDTO
from core.product.dto.inventory_update_dto import InventoryUpdateDTO

logger = logging.getLogger(__name__)


class ProductService:
    """
    Service for managing products and inventory.
    Handles CRUD operations for products and stock level management.
    When a product is created, an inventory record is automatically generated.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def generate_inventory_id(product_name: str) -> str:
        """
        Generate a unique inventory_id from product name.
        
        Args:
            product_name: Product name
            
        Returns:
            Formatted inventory_id (e.g., "PROD-WIRELESS-HEADPHONES-001")
        """
        # Convert to uppercase and replace spaces/special chars with hyphens
        inventory_id = re.sub(r'[^a-zA-Z0-9]', '-', product_name.strip().upper())
        # Remove consecutive hyphens
        inventory_id = re.sub(r'-+', '-', inventory_id)
        # Remove leading/trailing hyphens
        inventory_id = inventory_id.strip('-')
        return f"{inventory_id}"

    # ==================== PRODUCT METHODS ====================

    def create_product(self, product_data: ProductCreateDTO) -> Tuple[bool, Optional[Product], str]:
        """
        Create a new product and automatically create an associated inventory record.

        Args:
            product_data: ProductCreateDTO with product details

        Returns:
            Tuple of (success, product_object, message)
        """
        try:
            logger.info(f"[PRODUCT_SERVICE] Creating product: {product_data.name}")

            # Generate inventory_id from product name
            inventory_id = self.generate_inventory_id(product_data.name)
            
            # Check if inventory_id already exists
            existing = self.db.query(Product).filter(Product.inventory_id == inventory_id).first()
            if existing:
                return False, None, f"Product with inventory_id {inventory_id} already exists. Try a different product name."

            # Check if barcode already exists (if provided)
            if product_data.barcode:
                existing = self.db.query(Product).filter(Product.barcode == product_data.barcode).first()
                if existing:
                    return False, None, f"Product with barcode {product_data.barcode} already exists"

            # Create product
            product = Product(
                inventory_id=inventory_id,
                barcode=product_data.barcode,
                name=product_data.name,
                description=product_data.description,
                category=product_data.category,
                brand=product_data.brand,
                tags=product_data.tags,
                attributes=product_data.attributes
            )

            self.db.add(product)
            self.db.flush()  # Flush to get the product_id before creating inventory
            
            # Automatically create an inventory record for the new product
            inventory = Inventory(
                product_id=product.product_id,
                location=None,  # Default location is None
                name=f"{product_data.name} - Default Inventory",
                quantity_on_hand=0,
                quantity_reserved=0,
                quantity_in_transit=0,
                quantity_on_order=0,
                quantity_backordered=0,
                min_stock_level=None,
                max_stock_level=None,
                reorder_point=None,
                reorder_quantity=None,
                optimal_stock_level=None,
                stockout_risk_score=None,
                days_of_inventory=None
            )
            
            self.db.add(inventory)
            self.db.commit()
            self.db.refresh(product)

            logger.info(f"[PRODUCT_SERVICE] Product created successfully: {product.inventory_id} with inventory_id: {inventory.inventory_id}")
            return True, product, f"Product {product.inventory_id} created successfully with automatic inventory!"

        except Exception as e:
            self.db.rollback()
            logger.error(f"[PRODUCT_SERVICE] Error creating product: {str(e)}", exc_info=True)
            return False, None, f"Error creating product: {str(e)}"

    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Get a product by its ID."""
        try:
            logger.info(f"[PRODUCT_SERVICE] Fetching product: {product_id}")
            product = self.db.query(Product).filter(Product.product_id == uuid.UUID(product_id)).first()
            return product
        except Exception as e:
            logger.error(f"[PRODUCT_SERVICE] Error fetching product: {str(e)}", exc_info=True)
            return None

    def get_product_by_inventory_id(self, inventory_id: str) -> Optional[Product]:
        """Get a product by its inventory ID."""
        try:
            logger.info(f"[PRODUCT_SERVICE] Fetching product by inventory_id: {inventory_id}")
            product = self.db.query(Product).filter(Product.inventory_id == inventory_id).first()
            return product
        except Exception as e:
            logger.error(f"[PRODUCT_SERVICE] Error fetching product: {str(e)}", exc_info=True)
            return None

    def get_product_by_barcode(self, barcode: str) -> Optional[Product]:
        """Get a product by its barcode."""
        try:
            logger.info(f"[PRODUCT_SERVICE] Fetching product by barcode: {barcode}")
            product = self.db.query(Product).filter(Product.barcode == barcode).first()
            return product
        except Exception as e:
            logger.error(f"[PRODUCT_SERVICE] Error fetching product: {str(e)}", exc_info=True)
            return None

    def get_all_products(self, skip: int = 0, limit: int = 100, category: Optional[str] = None) -> List[Product]:
        """Get all products with optional filtering."""
        try:
            query = self.db.query(Product)
            
            if category:
                query = query.filter(Product.category == category)

            products = query.order_by(desc(Product.created_at)).offset(skip).limit(limit).all()
            logger.info(f"[PRODUCT_SERVICE] Found {len(products)} products")
            return products
        except Exception as e:
            logger.error(f"[PRODUCT_SERVICE] Error fetching products: {str(e)}", exc_info=True)
            return []

    def update_product(self, product_id: str, update_data: ProductUpdateDTO) -> Tuple[bool, Optional[Product], str]:
        """
        Update an existing product.

        Args:
            product_id: Product ID
            update_data: ProductUpdateDTO with fields to update

        Returns:
            Tuple of (success, product_object, message)
        """
        try:
            logger.info(f"[PRODUCT_SERVICE] Updating product: {product_id}")

            product = self.get_product_by_id(product_id)
            if not product:
                return False, None, "Product not found"

            # Check barcode uniqueness if being updated
            if update_data.barcode and update_data.barcode != product.barcode:
                existing = self.db.query(Product).filter(
                    Product.barcode == update_data.barcode,
                    Product.product_id != uuid.UUID(product_id)
                ).first()
                if existing:
                    return False, None, f"Product with barcode {update_data.barcode} already exists"

            # Update fields
            if update_data.name:
                product.name = update_data.name

            if update_data.description is not None:
                product.description = update_data.description

            if update_data.category:
                product.category = update_data.category

            if update_data.brand:
                product.brand = update_data.brand

            if update_data.barcode is not None:
                product.barcode = update_data.barcode

            if update_data.tags is not None:
                product.tags = update_data.tags

            if update_data.attributes is not None:
                product.attributes = update_data.attributes

            product.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(product)

            logger.info(f"[PRODUCT_SERVICE] Product updated successfully: {product.inventory_id}")
            return True, product, f"Product {product.inventory_id} updated successfully!"

        except Exception as e:
            self.db.rollback()
            logger.error(f"[PRODUCT_SERVICE] Error updating product: {str(e)}", exc_info=True)
            return False, None, f"Error updating product: {str(e)}"

    def delete_product(self, product_id: str) -> Tuple[bool, str]:
        """Delete a product (and associated inventory)."""
        try:
            logger.info(f"[PRODUCT_SERVICE] Deleting product: {product_id}")

            product = self.get_product_by_id(product_id)
            if not product:
                return False, "Product not found"

            # Delete associated inventory records
            self.db.query(Inventory).filter(Inventory.product_id == uuid.UUID(product_id)).delete()

            # Delete product
            self.db.delete(product)
            self.db.commit()

            logger.info(f"[PRODUCT_SERVICE] Product deleted successfully: {product_id}")
            return True, "Product deleted successfully!"

        except Exception as e:
            self.db.rollback()
            logger.error(f"[PRODUCT_SERVICE] Error deleting product: {str(e)}", exc_info=True)
            return False, f"Error deleting product: {str(e)}"

    # ==================== INVENTORY METHODS ====================

    def create_inventory(self, inventory_data: InventoryCreateDTO) -> Tuple[bool, Optional[Inventory], str]:
        """
        Create inventory for a product.

        Args:
            inventory_data: InventoryCreateDTO with inventory details

        Returns:
            Tuple of (success, inventory_object, message)
        """
        try:
            logger.info(f"[PRODUCT_SERVICE] Creating inventory for product: {inventory_data.product_id}")

            # Verify product exists
            product = self.get_product_by_id(inventory_data.product_id)
            if not product:
                return False, None, "Product not found"

            # Check for duplicate location for same product
            existing = self.db.query(Inventory).filter(
                Inventory.product_id == uuid.UUID(inventory_data.product_id),
                Inventory.location == inventory_data.location
            ).first()
            if existing:
                return False, None, f"Inventory already exists for this product at location {inventory_data.location}"

            # Create inventory
            inventory = Inventory(
                product_id=uuid.UUID(inventory_data.product_id),
                location=inventory_data.location,
                name=inventory_data.name,
                quantity_on_hand=inventory_data.quantity_on_hand,
                quantity_reserved=inventory_data.quantity_reserved,
                quantity_in_transit=inventory_data.quantity_in_transit,
                quantity_on_order=inventory_data.quantity_on_order,
                quantity_backordered=inventory_data.quantity_backordered,
                min_stock_level=inventory_data.min_stock_level,
                max_stock_level=inventory_data.max_stock_level,
                reorder_point=inventory_data.reorder_point,
                reorder_quantity=inventory_data.reorder_quantity,
                optimal_stock_level=inventory_data.optimal_stock_level,
                stockout_risk_score=inventory_data.stockout_risk_score,
                days_of_inventory=inventory_data.days_of_inventory
            )

            self.db.add(inventory)
            self.db.commit()
            self.db.refresh(inventory)

            logger.info(f"[PRODUCT_SERVICE] Inventory created successfully for product: {inventory_data.product_id}")
            return True, inventory, "Inventory created successfully!"

        except Exception as e:
            self.db.rollback()
            logger.error(f"[PRODUCT_SERVICE] Error creating inventory: {str(e)}", exc_info=True)
            return False, None, f"Error creating inventory: {str(e)}"

    def get_inventory_by_id(self, inventory_id: str) -> Optional[Inventory]:
        """Get inventory by its ID."""
        try:
            logger.info(f"[PRODUCT_SERVICE] Fetching inventory: {inventory_id}")
            inventory = self.db.query(Inventory).filter(Inventory.inventory_id == uuid.UUID(inventory_id)).first()
            return inventory
        except Exception as e:
            logger.error(f"[PRODUCT_SERVICE] Error fetching inventory: {str(e)}", exc_info=True)
            return None

    def get_product_inventory(self, product_id: str, location: Optional[str] = None) -> List[Inventory]:
        """Get inventory for a product, optionally filtered by location."""
        try:
            logger.info(f"[PRODUCT_SERVICE] Fetching inventory for product: {product_id}")
            query = self.db.query(Inventory).filter(Inventory.product_id == uuid.UUID(product_id))

            if location:
                query = query.filter(Inventory.location == location)

            inventory = query.all()
            logger.info(f"[PRODUCT_SERVICE] Found {len(inventory)} inventory records")
            return inventory
        except Exception as e:
            logger.error(f"[PRODUCT_SERVICE] Error fetching inventory: {str(e)}", exc_info=True)
            return []

    def get_all_inventory(self, skip: int = 0, limit: int = 100) -> List[Inventory]:
        """Get all inventory records."""
        try:
            inventory = self.db.query(Inventory).order_by(desc(Inventory.updated_at)).offset(skip).limit(limit).all()
            logger.info(f"[PRODUCT_SERVICE] Found {len(inventory)} inventory records")
            return inventory
        except Exception as e:
            logger.error(f"[PRODUCT_SERVICE] Error fetching inventory: {str(e)}", exc_info=True)
            return []

    def update_inventory(self, inventory_id: str, update_data: InventoryUpdateDTO) -> Tuple[bool, Optional[Inventory], str]:
        """
        Update inventory.

        Args:
            inventory_id: Inventory ID
            update_data: InventoryUpdateDTO with fields to update

        Returns:
            Tuple of (success, inventory_object, message)
        """
        try:
            logger.info(f"[PRODUCT_SERVICE] Updating inventory: {inventory_id}")

            inventory = self.get_inventory_by_id(inventory_id)
            if not inventory:
                return False, None, "Inventory not found"

            # Update quantities
            if update_data.quantity_on_hand is not None:
                inventory.quantity_on_hand = update_data.quantity_on_hand

            if update_data.quantity_reserved is not None:
                inventory.quantity_reserved = update_data.quantity_reserved

            if update_data.quantity_in_transit is not None:
                inventory.quantity_in_transit = update_data.quantity_in_transit

            if update_data.quantity_on_order is not None:
                inventory.quantity_on_order = update_data.quantity_on_order

            if update_data.quantity_backordered is not None:
                inventory.quantity_backordered = update_data.quantity_backordered

            # Update stock levels
            if update_data.min_stock_level is not None:
                inventory.min_stock_level = update_data.min_stock_level

            if update_data.max_stock_level is not None:
                inventory.max_stock_level = update_data.max_stock_level

            if update_data.reorder_point is not None:
                inventory.reorder_point = update_data.reorder_point

            if update_data.reorder_quantity is not None:
                inventory.reorder_quantity = update_data.reorder_quantity

            # Update AI fields
            if update_data.optimal_stock_level is not None:
                inventory.optimal_stock_level = update_data.optimal_stock_level

            if update_data.stockout_risk_score is not None:
                inventory.stockout_risk_score = update_data.stockout_risk_score

            if update_data.days_of_inventory is not None:
                inventory.days_of_inventory = update_data.days_of_inventory

            # Update location
            if update_data.location is not None:
                inventory.location = update_data.location

            # Update name
            if update_data.name is not None:
                inventory.name = update_data.name

            inventory.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(inventory)

            logger.info(f"[PRODUCT_SERVICE] Inventory updated successfully: {inventory_id}")
            return True, inventory, "Inventory updated successfully!"

        except Exception as e:
            self.db.rollback()
            logger.error(f"[PRODUCT_SERVICE] Error updating inventory: {str(e)}", exc_info=True)
            return False, None, f"Error updating inventory: {str(e)}"

    def delete_inventory(self, inventory_id: str) -> Tuple[bool, str]:
        """Delete inventory record."""
        try:
            logger.info(f"[PRODUCT_SERVICE] Deleting inventory: {inventory_id}")

            inventory = self.get_inventory_by_id(inventory_id)
            if not inventory:
                return False, "Inventory not found"

            self.db.delete(inventory)
            self.db.commit()

            logger.info(f"[PRODUCT_SERVICE] Inventory deleted successfully: {inventory_id}")
            return True, "Inventory deleted successfully!"

        except Exception as e:
            self.db.rollback()
            logger.error(f"[PRODUCT_SERVICE] Error deleting inventory: {str(e)}", exc_info=True)
            return False, f"Error deleting inventory: {str(e)}"

    def get_low_stock_items(self, threshold: float = 0.5) -> List[Inventory]:
        """Get inventory items below reorder point.
        
        Args:
            threshold: Multiplier for reorder point (default 0.5 = 50% of reorder point)
        
        Returns:
            List of inventory records below threshold
        """
        try:
            logger.info(f"[PRODUCT_SERVICE] Fetching low stock items")
            # Get items where quantity_available < (reorder_point * threshold)
            inventory = self.db.query(Inventory).filter(
                Inventory.reorder_point.isnot(None),
                (Inventory.quantity_on_hand - Inventory.quantity_reserved) < 
                (Inventory.reorder_point * threshold)
            ).all()
            logger.info(f"[PRODUCT_SERVICE] Found {len(inventory)} low stock items")
            return inventory
        except Exception as e:
            logger.error(f"[PRODUCT_SERVICE] Error fetching low stock items: {str(e)}", exc_info=True)
            return []
