package com.vemins.esp.math

import com.vemins.esp.model.MinimapConfig
import kotlin.math.atan2
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Mathematical helper extension on Float to safely coerce values within [minVal, maxVal]
 * even if minVal > maxVal (e.g. unmeasured or zero screen viewports) or if NaN/Infinite values occur,
 * preventing `IllegalArgumentException: Cannot coerce value to an empty range`.
 */
fun Float.safeCoerceIn(minVal: Float, maxVal: Float): Float {
    if (this.isNaN()) return if (!minVal.isNaN()) minVal else 0.0f
    if (minVal.isNaN() || maxVal.isNaN()) return this
    if (minVal > maxVal) return minVal
    return this.coerceIn(minVal, maxVal)
}

/**
 * Reusable mutable result container for zero-allocation isometric projection calculations.
 */
data class IsometricResult(
    var screenX: Float = 0.0f,
    var screenY: Float = 0.0f,
    var isOnScreen: Boolean = false,
    var distanceM: Float = 0.0f
) {
    fun set(sx: Float, sy: Float, onScreen: Boolean, dist: Float): IsometricResult {
        screenX = sx
        screenY = sy
        isOnScreen = onScreen
        distanceM = dist
        return this
    }
}

/**
 * Reusable mutable result container for off-screen edge radar clamping calculations.
 */
data class EdgeRadarResult(
    var clampedX: Float = 0.0f,
    var clampedY: Float = 0.0f,
    var angleDeg: Float = 0.0f
) {
    fun set(cx: Float, cy: Float, angle: Float): EdgeRadarResult {
        clampedX = cx
        clampedY = cy
        angleDeg = angle
        return this
    }
}

/**
 * High-Performance 3D-to-2D Isometric Camera Projection & Perimeter Radar Engine.
 *
 * MLBB utilizes a fixed 45°/55° isometric pitch camera centered on the local hero.
 * This class projects relative world coordinates $(\Delta x, \Delta y)$ onto the active screen viewport
 * and provides edge radar perimeter raycasting for off-screen targets.
 *
 * Mathematical Projection Formulas:
 * $$\Delta x = X_{\text{target}} - X_{\text{self}}, \quad \Delta y = Y_{\text{target}} - Y_{\text{self}}$$
 * $$iso_x = (\Delta x - \Delta y) \cdot \frac{\sqrt{2}}{2}$$
 * $$iso_y = (\Delta x + \Delta y) \cdot \frac{\sqrt{2}}{2}$$
 * $$X_{\text{hud}} = cx + (iso_x \cdot S_x)$$
 * $$Y_{\text{hud}} = cy - (iso_y \cdot S_y) - H_{\text{offset}}$$
 */
class IsometricProjection(config: MinimapConfig = MinimapConfig()) {

    companion object {
        /** $\frac{\sqrt{2}}{2} = \cos(45^\circ) = \sin(45^\circ) \approx 0.70710678$ */
        const val ISO_FACTOR: Float = 0.7071067811865475f
    }

    var screenWidth: Float = config.screenWidth
        private set
    var screenHeight: Float = config.screenHeight
        private set
    var screenCenterX: Float = config.screenCenterX
        private set
    var screenCenterY: Float = config.screenCenterY
        private set

    var scaleX: Float = config.scaleX
        private set
    var scaleY: Float = config.scaleY
        private set
    var hudOffsetY: Float = config.hudOffsetY
        private set
    var camOffsetX: Float = config.camOffsetX
        private set
    var camOffsetY: Float = config.camOffsetY
        private set
    var edgeMargin: Float = config.edgeMargin
        private set
    var maxRadarDistance: Float = config.maxRadarDistance
        private set
    var rotationDegrees: Float = config.rotationDegrees
        private set

    var usePerspective: Boolean = config.usePerspective
        private set
    var cameraPitch: Float = config.cameraPitch
        private set
    var highCamera: Boolean = config.highCamera
        private set

    private var rotationRad: Float = Math.toRadians(config.rotationDegrees.toDouble()).toFloat()
    private var cosRot: Float = kotlin.math.cos(rotationRad)
    private var sinRot: Float = kotlin.math.sin(rotationRad)

    init {
        updateConfig(config)
    }

    /**
     * Updates projection and camera calibration settings.
     */
    fun updateConfig(config: MinimapConfig) {
        screenWidth = config.screenWidth
        screenHeight = config.screenHeight
        screenCenterX = config.screenCenterX
        screenCenterY = config.screenCenterY

        scaleX = config.scaleX
        val pitchMultiplier = if (config.highCamera) 0.88f else 1.0f
        scaleY = config.scaleY * pitchMultiplier
        hudOffsetY = config.hudOffsetY
        camOffsetX = config.camOffsetX
        camOffsetY = config.camOffsetY
        edgeMargin = config.edgeMargin
        maxRadarDistance = config.maxRadarDistance
        rotationDegrees = config.rotationDegrees
        highCamera = config.highCamera
        usePerspective = config.usePerspective
        cameraPitch = config.cameraPitch

        rotationRad = Math.toRadians(config.rotationDegrees.toDouble()).toFloat()
        cosRot = kotlin.math.cos(rotationRad)
        sinRot = kotlin.math.sin(rotationRad)
    }

    /**
     * Transforms relative Cartesian world coordinates into 2D pixel coordinates on the main screen.
     * Zero-allocation pass writing output into [outResult].
     *
     * In MLBB, the combat world camera is anchored at a fixed 45° ground yaw.
     * Minimap rotation (315°/135°) applies exclusively to the 2D minimap radar,
     * so 3D world projection is decoupled from minimap rotation to eliminate lateral drift.
     *
     * @param targetX World X coordinate of target entity.
     * @param targetY World Y coordinate of target entity.
     * @param localX World X coordinate of local hero or camera center.
     * @param localY World Y coordinate of local hero or camera center.
     * @param customHudOffsetY Optional custom vertical pixel lift; defaults to configured hudOffsetY if null.
     * @param outResult Output [IsometricResult] container.
     * @return [outResult] populated with projected screen coordinate, on-screen flag, and world distance.
     */
    fun worldToScreen(
        targetX: Float,
        targetY: Float,
        localX: Float,
        localY: Float,
        customHudOffsetY: Float? = null,
        outResult: IsometricResult
    ): IsometricResult {
        val dx = targetX - localX
        val dy = targetY - localY

        // Distance in world meters
        val distM = sqrt(dx * dx + dy * dy)

        // MLBB fixed 45° isometric ground camera projection:
        // isoX = (dx - dy) * cos(45°), isoY = (dx + dy) * sin(45°)
        val isoX = (dx - dy) * ISO_FACTOR
        val isoY = (dx + dy) * ISO_FACTOR

        val lift = customHudOffsetY ?: hudOffsetY

        val cx = if (screenCenterX > 0.0f) screenCenterX else (if (screenWidth > 0.0f) screenWidth / 2.0f else 0.0f)
        val cy = if (screenCenterY > 0.0f) screenCenterY else (if (screenHeight > 0.0f) screenHeight / 2.0f else 0.0f)

        if (usePerspective) {
            val pitchRad = Math.toRadians(cameraPitch.toDouble()).toFloat()
            val cosPitch = kotlin.math.cos(pitchRad)
            val camHeight = if (highCamera) 30.0f else 26.0f

            // Depth along camera line of sight (Z_depth)
            val depth = (camHeight + (isoY * cosPitch)).coerceAtLeast(6.0f)
            val perspScale = camHeight / depth

            val sx = cx + ((isoX * scaleX) * perspScale) + camOffsetX
            val sy = cy - (((isoY * scaleY) + lift) * perspScale) + camOffsetY
            val onScreen = screenWidth > 0.0f && screenHeight > 0.0f && sx in 0.0f..screenWidth && sy in 0.0f..screenHeight
            return outResult.set(sx, sy, onScreen, distM)
        } else {
            // True axonometric orthographic projection with pixel lift and fine offsets
            val sx = cx + (isoX * scaleX) + camOffsetX
            val sy = cy - (isoY * scaleY) - lift + camOffsetY
            val onScreen = screenWidth > 0.0f && screenHeight > 0.0f && sx in 0.0f..screenWidth && sy in 0.0f..screenHeight
            return outResult.set(sx, sy, onScreen, distM)
        }
    }

    /**
     * Convenience method returning a new [IsometricResult] instance.
     */
    fun worldToScreen(
        targetX: Float,
        targetY: Float,
        localX: Float,
        localY: Float,
        customHudOffsetY: Float? = null
    ): IsometricResult {
        return worldToScreen(targetX, targetY, localX, localY, customHudOffsetY, IsometricResult())
    }

    /**
     * For off-screen targets, projects a ray from screen center to (screenX, screenY),
     * clamping it to the screen border inset by [edgeMargin].
     * Zero-allocation pass writing output into [outResult].
     *
     * @param screenX Unclamped off-screen X pixel coordinate.
     * @param screenY Unclamped off-screen Y pixel coordinate.
     * @param customMargin Optional margin override; defaults to configured edgeMargin if null.
     * @param outResult Output [EdgeRadarResult] container.
     * @return [outResult] populated with clamped border coordinate $(X_c, Y_c)$ and heading angle in degrees.
     */
    fun calculateEdgeRadar(
        screenX: Float,
        screenY: Float,
        customMargin: Float? = null,
        outResult: EdgeRadarResult
    ): EdgeRadarResult {
        if (screenWidth <= 0.0f || screenHeight <= 0.0f) {
            return outResult.set(0.0f, 0.0f, 0.0f)
        }

        val maxAllowedPad = min(screenWidth, screenHeight) / 2.0f
        val pad = (customMargin ?: edgeMargin).safeCoerceIn(0.0f, maxAllowedPad)
        val minX = pad
        val maxX = (screenWidth - pad).coerceAtLeast(minX)
        val minY = pad
        val maxY = (screenHeight - pad).coerceAtLeast(minY)

        val cx = if (screenCenterX > 0.0f) screenCenterX else screenWidth / 2.0f
        val cy = if (screenCenterY > 0.0f) screenCenterY else screenHeight / 2.0f

        val vx = screenX - cx
        val vy = screenY - cy

        val angleDeg = Math.toDegrees(atan2(vy.toDouble(), vx.toDouble())).toFloat()

        var minT = Float.MAX_VALUE

        // Test X border intersection
        if (vx > 0.001f) {
            val tx = (maxX - cx) / vx
            if (tx >= 0.0f && tx < minT) minT = tx
        } else if (vx < -0.001f) {
            val tx = (minX - cx) / vx
            if (tx >= 0.0f && tx < minT) minT = tx
        }

        // Test Y border intersection
        if (vy > 0.001f) {
            val ty = (maxY - cy) / vy
            if (ty >= 0.0f && ty < minT) minT = ty
        } else if (vy < -0.001f) {
            val ty = (minY - cy) / vy
            if (ty >= 0.0f && ty < minT) minT = ty
        }

        val t = if (minT != Float.MAX_VALUE) minT.coerceAtLeast(0.0f) else 1.0f

        val clampedX = (cx + vx * t).safeCoerceIn(minX, maxX)
        val clampedY = (cy + vy * t).safeCoerceIn(minY, maxY)

        return outResult.set(clampedX, clampedY, angleDeg)
    }

    /**
     * Convenience method returning a new [EdgeRadarResult] instance.
     */
    fun calculateEdgeRadar(screenX: Float, screenY: Float, customMargin: Float? = null): EdgeRadarResult {
        return calculateEdgeRadar(screenX, screenY, customMargin, EdgeRadarResult())
    }

    /**
     * Euclidean 2D distance calculation in world meters.
     */
    fun calculateDistanceM(x1: Float, y1: Float, x2: Float, y2: Float): Float {
        val dx = x2 - x1
        val dy = y2 - y1
        return sqrt(dx * dx + dy * dy)
    }
}

