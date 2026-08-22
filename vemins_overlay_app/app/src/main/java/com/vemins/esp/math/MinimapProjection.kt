package com.vemins.esp.math

import com.vemins.esp.model.MinimapConfig
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Reusable mutable 2D point container for zero-allocation projection passes.
 */
data class Point2D(
    var x: Float = 0.0f,
    var y: Float = 0.0f
) {
    fun set(newX: Float, newY: Float): Point2D {
        x = newX
        y = newY
        return this
    }
}

/**
 * High-Performance 2D Minimap Projection Engine with 45° Diamond Coordinate Geometry.
 *
 * MLBB's map is oriented diagonally. This engine transforms Cartesian world coordinates
 * $(X_w, Y_w) \in [-52.0, +52.0]$ onto the 2D top-left radar viewport using both standard linear
 * mapping and the authoritative 45° Diamond Rotation Matrix:
 *
 * $$x_{\text{rot}} = \frac{x - y}{\sqrt{2}}$$
 * $$y_{\text{rot}} = \frac{x + y}{\sqrt{2}}$$
 *
 * Features:
 * 1. 45° Diamond Coordinate Transformation for battlefield radar alignment.
 * 2. 45° Rotation for entity movement heading / velocity vector arrows.
 * 3. Linear Normalization with screen Y-axis inversion (top-to-bottom pixel layout).
 * 4. Zero-allocation per-frame execution via reusable [Point2D] scratch buffers.
 */
class MinimapProjection(config: MinimapConfig = MinimapConfig()) {

    companion object {
        /** $\frac{1}{\sqrt{2}} = \cos(45^\circ) = \sin(45^\circ) \approx 0.70710678$ */
        const val INV_SQRT2: Float = 0.7071067811865475f

        /** $\sqrt{2} \approx 1.41421356$ */
        const val SQRT2: Float = 1.4142135623730951f

        /**
         * Pure 45° diamond coordinate rotation:
         * $x_{\text{rot}} = (x - y) / \sqrt{2}$, $y_{\text{rot}} = (x + y) / \sqrt{2}$
         */
        @JvmStatic
        fun rotateDiamond(x: Float, y: Float, outPoint: Point2D): Point2D {
            val rx = (x - y) * INV_SQRT2
            val ry = (x + y) * INV_SQRT2
            return outPoint.set(rx, ry)
        }
    }

    // Viewport Parameters
    var mapX: Float = config.mapPosX
        private set
    var mapY: Float = config.mapPosY
        private set
    var mapWidth: Float = config.mapWidth
        private set
    var mapHeight: Float = config.mapHeight
        private set
    var invertY: Boolean = config.invertY
        private set

    // World Cartesian Coordinate Bounds
    var minX: Float = config.minX
        private set
    var maxX: Float = config.maxX
        private set
    var minY: Float = config.minY
        private set
    var maxY: Float = config.maxY
        private set

    var worldW: Float = config.worldWidth
        private set
    var worldH: Float = config.worldHeight
        private set

    // Rotated Coordinate Bounds for Diamond Map Projection
    private var rotMinX: Float = -52.0f * INV_SQRT2
    private var rotMaxX: Float = 52.0f * INV_SQRT2
    private var rotMinY: Float = -52.0f * INV_SQRT2
    private var rotMaxY: Float = 52.0f * INV_SQRT2
    private var rotWorldW: Float = 104.0f * INV_SQRT2
    private var rotWorldH: Float = 104.0f * INV_SQRT2

    // Custom Angle Rotation Precomputations
    private var rotationRad: Float = Math.toRadians(config.rotationDegrees.toDouble()).toFloat()
    private var cosRot: Float = cos(rotationRad)
    private var sinRot: Float = sin(rotationRad)
    private var isCustomRotated: Boolean = config.rotationDegrees != 0.0f

    private var mapCenterX: Float = mapX + mapWidth / 2.0f
    private var mapCenterY: Float = mapY + mapHeight / 2.0f

    init {
        updateConfig(config)
    }

    /**
     * Updates projection parameters and recalculates cached geometric transforms.
     */
    @Synchronized
    fun updateConfig(config: MinimapConfig) {
        mapX = config.mapPosX
        mapY = config.mapPosY
        mapWidth = config.mapWidth
        mapHeight = config.mapHeight
        invertY = config.invertY

        minX = config.minX
        maxX = config.maxX
        minY = config.minY
        maxY = config.maxY

        worldW = if (maxX != minX) maxX - minX else 104.0f
        worldH = if (maxY != minY) maxY - minY else 104.0f

        val halfSpan = Math.max(Math.abs(maxX - minX), Math.abs(maxY - minY)) / 2.0f
        val maxExtentRot = halfSpan * INV_SQRT2
        rotMinX = -maxExtentRot
        rotMaxX = maxExtentRot
        rotMinY = -maxExtentRot
        rotMaxY = maxExtentRot
        rotWorldW = rotMaxX - rotMinX
        rotWorldH = rotMaxY - rotMinY

        val deg = config.rotationDegrees
        isCustomRotated = deg != 0.0f
        rotationRad = Math.toRadians(deg.toDouble()).toFloat()
        cosRot = cos(rotationRad)
        sinRot = sin(rotationRad)

        mapCenterX = mapX + mapWidth / 2.0f
        mapCenterY = mapY + mapHeight / 2.0f
    }

    /**
     * Projects world coordinates $(X_w, Y_w)$ to screen pixel coordinates on the minimap.
     * Zero-allocation pass writing output into [outPoint].
     *
     * @param worldX World Cartesian X coordinate in units $[-52.0, 52.0]$.
     * @param worldY World Cartesian Y coordinate in units $[-52.0, 52.0]$.
     * @param outPoint Output [Point2D] container to populate.
     * @param useDiamond If true, applies 45° diamond matrix projection before viewport mapping.
     * @return [outPoint] populated with projected screen coordinates $(X_m, Y_m)$.
     */
    fun worldToMinimap(
        worldX: Float,
        worldY: Float,
        outPoint: Point2D,
        useDiamond: Boolean = true
    ): Point2D {
        if (useDiamond) {
            return worldToMinimapDiamond(worldX, worldY, outPoint)
        }

        var normX = (worldX - minX) / worldW
        var normY = (worldY - minY) / worldH

        normX = normX.coerceIn(0.0f, 1.0f)
        normY = normY.coerceIn(0.0f, 1.0f)

        if (!isCustomRotated) {
            val sx = mapX + (normX * mapWidth)
            val sy = if (invertY) {
                mapY + ((1.0f - normY) * mapHeight)
            } else {
                mapY + (normY * mapHeight)
            }
            return outPoint.set(sx, sy)
        } else {
            val unrotatedOffsetX = (normX - 0.5f) * mapWidth
            val unrotatedOffsetY = if (invertY) {
                ((1.0f - normY) - 0.5f) * mapHeight
            } else {
                (normY - 0.5f) * mapHeight
            }

            val rotX = unrotatedOffsetX * cosRot - unrotatedOffsetY * sinRot
            val rotY = unrotatedOffsetX * sinRot + unrotatedOffsetY * cosRot

            val sx = mapCenterX + rotX
            val sy = mapCenterY + rotY
            return outPoint.set(sx, sy)
        }
    }

    /**
     * Convenience method returning a new [Point2D] instance.
     */
    fun worldToMinimap(worldX: Float, worldY: Float): Point2D {
        return worldToMinimap(worldX, worldY, Point2D(), useDiamond = true)
    }

    /**
     * Applies the 45° Diamond rotation matrix $(x-y)/\sqrt{2}, (x+y)/\sqrt{2}$ and projects to the minimap.
     */
    fun worldToMinimapDiamond(worldX: Float, worldY: Float, outPoint: Point2D): Point2D {
        // 45° diamond transform
        val rotX = (worldX - worldY) * INV_SQRT2
        val rotY = (worldX + worldY) * INV_SQRT2

        var normX = (rotX - rotMinX) / rotWorldW
        var normY = (rotY - rotMinY) / rotWorldH

        normX = normX.coerceIn(0.0f, 1.0f)
        normY = normY.coerceIn(0.0f, 1.0f)

        val sx = mapX + (normX * mapWidth)
        val sy = if (invertY) {
            mapY + ((1.0f - normY) * mapHeight)
        } else {
            mapY + (normY * mapHeight)
        }

        return outPoint.set(sx, sy)
    }

    /**
     * Calculates the endpoint of a heading / velocity arrow originating from (screenX, screenY).
     * Rotates heading direction vectors by 45° if [rotate45] is enabled.
     * Zero-allocation pass writing output into [outPoint].
     *
     * @param screenX Minimap screen X origin.
     * @param screenY Minimap screen Y origin.
     * @param dirX Facing / direction vector X component.
     * @param dirY Facing / direction vector Y component.
     * @param length Desired arrow length in screen pixels.
     * @param outPoint Output [Point2D] container to populate with arrow tip coordinate.
     * @param rotate45 If true, applies 45° diamond vector rotation.
     * @return [outPoint] populated with arrow endpoint.
     */
    fun calculateDirectionArrow(
        screenX: Float,
        screenY: Float,
        dirX: Float,
        dirY: Float,
        length: Float,
        outPoint: Point2D,
        rotate45: Boolean = false
    ): Point2D {
        val mag = sqrt(dirX * dirX + dirY * dirY)
        if (mag < 0.001f) {
            return outPoint.set(screenX, screenY)
        }

        var ndx = dirX / mag
        var ndy = dirY / mag

        // 45-degree diamond vector rotation
        if (rotate45) {
            val rdx = (ndx - ndy) * INV_SQRT2
            val rdy = (ndx + ndy) * INV_SQRT2
            ndx = rdx
            ndy = rdy
        } else if (isCustomRotated) {
            val rdx = ndx * cosRot - ndy * sinRot
            val rdy = ndx * sinRot + ndy * cosRot
            ndx = rdx
            ndy = rdy
        }

        if (invertY) {
            ndy = -ndy
        }

        val endX = screenX + (ndx * length)
        val endY = screenY + (ndy * length)
        return outPoint.set(endX, endY)
    }

    /**
     * Convenience method calculating heading arrow with 45° diamond rotation enabled.
     */
    fun calculateDirectionArrowDiamond(
        screenX: Float,
        screenY: Float,
        dirX: Float,
        dirY: Float,
        length: Float,
        outPoint: Point2D
    ): Point2D {
        return calculateDirectionArrow(screenX, screenY, dirX, dirY, length, outPoint, rotate45 = true)
    }

    /**
     * Checks whether a screen coordinate falls within the minimap bounding box.
     */
    fun isInMinimapBounds(screenX: Float, screenY: Float): Boolean {
        return screenX in mapX..(mapX + mapWidth) && screenY in mapY..(mapY + mapHeight)
    }
}
