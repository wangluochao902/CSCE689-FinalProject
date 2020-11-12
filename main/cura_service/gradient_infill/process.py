#!/usr/bin/env python3
"""
Gradient Infill for 3D prints.

License: MIT
Author: Stefan Hermann - CNC Kitchen
Version: 1.0
"""
import re
from collections import namedtuple
from enum import Enum
from typing import List, Tuple
import sys
import os

__version__ = '1.0'


class InfillType(Enum):
    """Enum for infill type."""

    SMALL_SEGMENTS = 1  # infill with small segments like honeycomb or gyroid
    LINEAR = 2  # linear infill like rectilinear or triangles


Point2D = namedtuple('Point2D', 'x y')
Segment = namedtuple('Segment', 'point1 point2')


class Section(Enum):
    """Enum for section type."""

    NOTHING = 0
    INNER_WALL = 1
    INFILL = 2


def dist(segment: Segment, point: Point2D) -> float:
    """Calculate the distance from a point to a line with finite length.

    Args:
        segment (Segment): line used for distance calculation
        point (Point2D): point used for distance calculation

    Returns:
        float: distance between ``segment`` and ``point``
    """
    px = segment.point2.x - segment.point1.x
    py = segment.point2.y - segment.point1.y
    norm = px * px + py * py
    u = ((point.x - segment.point1.x) * px + (point.y - segment.point1.y) * py) / float(norm)
    if u > 1:
        u = 1
    elif u < 0:
        u = 0
    x = segment.point1.x + u * px
    y = segment.point1.y + u * py
    dx = x - point.x
    dy = y - point.y

    return (dx * dx + dy * dy) ** 0.5


def get_points_distance(point1: Point2D, point2: Point2D) -> float:
    """Calculate the euclidean distance between two points.

    Args:
        point1 (Point2D): first point
        point2 (Point2D): second point

    Returns:
        float: euclidean distance between the points
    """
    return ((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2) ** 0.5


def min_distance_from_segment(segment: Segment, segments: List[Segment]) -> float:
    """Calculate the minimum distance from the midpoint of ``segment`` to the nearest segment in ``segments``.

    Args:
        segment (Segment): segment to use for midpoint calculation
        segments (List[Segment]): segments list

    Returns:
        float: the smallest distance from the midpoint of ``segment`` to the nearest segment in the list
    """
    middlePoint = Point2D((segment.point1.x + segment.point2.x) / 2, (segment.point1.y + segment.point2.y) / 2)

    return min(dist(s, middlePoint) for s in segments)

def min_distance_from_target_points(segment: Segment, target_points: List[Point2D]) -> float:
    """Calculate the minimum distance from the midpoint of ``segment`` to the nearest point in ``target_points``
    """
    middlePoint = Point2D((segment.point1.x + segment.point2.x) / 2, (segment.point1.y + segment.point2.y) / 2)
    return min(get_points_distance(middlePoint, p) for p in target_points)

def getXY(currentLine: str) -> Point2D:
    """Create a ``Point2D`` object from a gcode line.

    Args:
        currentLine (str): gcode line

    Raises:
        SyntaxError: when the regular expressions cannot find the relevant coordinates in the gcode

    Returns:
        Point2D: the parsed coordinates
    """
    searchX = re.search(r"X(\d*\.?\d*)", currentLine)
    searchY = re.search(r"Y(\d*\.?\d*)", currentLine)
    if searchX and searchY:
        elementX = searchX.group(1)
        elementY = searchY.group(1)
    else:
        raise SyntaxError(f'Gcode file parsing error for line {currentLine}')

    return Point2D(float(elementX), float(elementY))


def mapRange(a: Tuple[float, float], b: Tuple[float, float], s: float) -> float:
    """Calculate a multiplier for the extrusion value from the distance to the perimeter.

    Args:
        a (Tuple[float, float]): a tuple containing:
            - a1 (float): the minimum distance to the perimeter (always zero at the moment)
            - a2 (float): the maximum distance to the perimeter where the interpolation is performed
        b (Tuple[float, float]): a tuple containing:
            - b1 (float): the maximum flow as a fraction
            - b2 (float): the minimum flow as a fraction
        s (float): the euclidean distance from the middle of a segment to the nearest perimeter

    Returns:
        float: a multiplier for the modified extrusion value
    """
    (a1, a2), (b1, b2) = a, b

    return b1 + ((s - a1) * (b2 - b1) / (a2 - a1))


def get_extrusion_command(x: float, y: float, extrusion: float) -> str:
    """Format a gcode string from the X, Y coordinates and extrusion value.

    Args:
        x (float): X coordinate
        y (float): Y coordinate
        extrusion (float): Extrusion value

    Returns:
        str: Gcode line
    """
    return "G1 X{} Y{} E{}\n".format(round(x, 3), round(y, 3), round(extrusion, 5))

def is_begin_layer_line(line: str) -> bool:
    """Check if current line is the start of a layer section.

    Args:
        line (str): Gcode line

    Returns:
        bool: True if the line is the start of a layer section
    """
    return line.startswith(";LAYER:")


def is_begin_inner_wall_line(line: str) -> bool:
    """Check if current line is the start of an inner wall section.

    Args:
        line (str): Gcode line

    Returns:
        bool: True if the line is the start of an inner wall section
    """
    return line.startswith(";TYPE:WALL-INNER")


def is_end_inner_wall_line(line: str) -> bool:
    """Check if current line is the start of an outer wall section.

    Args:
        line (str): Gcode line

    Returns:
        bool: True if the line is the start of an outer wall section
    """
    return line.startswith(";TYPE:WALL-OUTER")


def is_extrusion_line(line: str) -> bool:
    """Check if current line is a standard printing segment.

    Args:
        line (str): Gcode line

    Returns:
        bool: True if the line is a standard printing segment
    """
    return "G1" in line and " X" in line and "Y" in line and "E" in line


def is_begin_infill_segment_line(line: str) -> bool:
    """Check if current line is the start of an infill.

    Args:
        line (str): Gcode line

    Returns:
        bool: True if the line is the start of an infill section
    """
    return line.startswith(";TYPE:FILL")

def is_relative_position_mode(line: str) -> bool:
    """Check if current line is start of relative position mode. Some machine may use relative position mode temporary
    at the end of the printing process. Stop procesing when enter ralitive position mode.

    Args:
        line (str): Gcode line

    Return:
        bool: True if the line is start of relative postion mode
    """
    return line.strip().startswith('G91')


def process_gcode(
    input_file_name: str,
    output_file_name: str,
    infill_type: InfillType,
    max_flow: float,
    min_flow: float,
    infill_targets: List[Tuple[float]],
    enable_gradient: bool = False,
    gradual_speed: bool = True,
    layer_height: float = 0.2,
    gradient_discretization: float = 4,
    max_over_speed_factor: float = 200,
    min_over_speed_factor: float = 60
) -> None:
    """Parse input Gcode file and modify infill portions with an extrusion width gradient."""
    currentSection = Section.NOTHING
    lastPosition = Point2D(-10000, -10000)
    # gradientDiscretizationLength = thickness / gradient_discretization
    current_layer_number = 0
    effective_infill_targets = []

    with open(input_file_name, "r") as gcodeFile, open(output_file_name, "w+") as outputFile:
        stop_processing = False
        print(infill_targets)
        for currentLine in gcodeFile:
            if stop_processing:
                outputFile.write(currentLine)
                continue

            writtenToFile = 0
            if is_begin_layer_line(currentLine):
                perimeterSegments = []
                current_layer_number = int(currentLine.split(":")[-1])
                effective_infill_targets = []
                for target in infill_targets:
                    if target[2] <= current_layer_number * layer_height < target[2] + target[3]:
                        effective_infill_targets.append(target)
                # print("effective:", effective_infill_targets)

            if is_begin_inner_wall_line(currentLine):
                currentSection = Section.INNER_WALL

            # if currentSection == Section.INNER_WALL and is_extrusion_line(currentLine):
            #     perimeterSegments.append(Segment(getXY(currentLine), lastPosition))

            if is_end_inner_wall_line(currentLine):
                currentSection = Section.NOTHING

            if is_begin_infill_segment_line(currentLine):
                currentSection = Section.INFILL
                outputFile.write(currentLine)
                continue
            if is_relative_position_mode(currentLine):
                stop_processing = True
                outputFile.write(currentLine)
                continue

            if currentSection == Section.INFILL:
                if "F" in currentLine and "G1" in currentLine:
                    # python3.6+ f-string variant:
                    # outputFile.write("G1 F{ re.search(r"F(\d*\.?\d*)", currentLine).group(1)) }\n"
                    searchSpeed = re.search(r"F(\d*\.?\d*)", currentLine)
                    if searchSpeed:
                        current_feed=float(searchSpeed.group(1))
                        outputFile.write("G1 F{}\n".format(current_feed))
                    else:
                        raise SyntaxError(f'Gcode file parsing error for line {currentLine}')
                if "E" in currentLine and "G1" in currentLine and " X" in currentLine and "Y" in currentLine:
                    currentPosition = getXY(currentLine)
                    splitLine = currentLine.split(" ")

                    # if infill_type == InfillType.LINEAR:
                    #     # find extrusion length
                    #     for element in splitLine:
                    #         if "E" in element:
                    #             extrusionLength = float(element[1:])
                    #     segmentLength = get_points_distance(lastPosition, currentPosition)
                    #     segmentSteps = segmentLength / gradientDiscretizationLength
                    #     extrusionLengthPerSegment = extrusionLength / segmentSteps
                    #     segmentDirection = Point2D(
                    #         (currentPosition.x - lastPosition.x) / segmentLength * gradientDiscretizationLength,
                    #         (currentPosition.y - lastPosition.y) / segmentLength * gradientDiscretizationLength,
                    #     )
                    #     if segmentSteps >= 2:
                    #         for step in range(int(segmentSteps)):
                    #             segmentEnd = Point2D(
                    #                 lastPosition.x + segmentDirection.x, lastPosition.y + segmentDirection.y
                    #             )
                    #             shortestDistance = min_distance_from_target_points(
                    #                 Segment(lastPosition, segmentEnd), target_points
                    #             )
                    #             if shortestDistance < thickness:
                    #                 segmentExtrusion = extrusionLengthPerSegment * mapRange(
                    #                     (0, thickness), (max_flow / 100, min_flow / 100), shortestDistance
                    #                 )
                    #             else:
                    #                 segmentExtrusion = extrusionLengthPerSegment * min_flow / 100

                    #             segmentFeed = current_feed / mapRange((0, thickness), (max_flow / 100, min_flow / 100), shortestDistance)

                    #             if gradual_speed:
                    #                 if segmentFeed > (current_feed * max_over_speed_factor/100):
                    #                     segmentFeed = current_feed * max_over_speed_factor/100
                    #                 if segmentFeed < (current_feed * min_over_speed_factor/100):
                    #                     segmentFeed = current_feed * min_over_speed_factor/100
                    #                 stringFeed = " F{}".format(int(segmentFeed))
                    #             outputFile.write(get_extrusion_command(segmentEnd.x, segmentEnd.y, segmentExtrusion) + stringFeed + "\n")
                    #             lastPosition = segmentEnd
                    #         # MissingSegment
                    #         segmentLengthRatio = get_points_distance(lastPosition, currentPosition) / segmentLength
                    #         segmentFeed = current_feed / ( max_flow / 100 )
                    #         if segmentFeed < (current_feed * min_over_speed_factor):
                    #             segmentFeed = current_feed * min_over_speed_factor
                    #         if gradual_speed:
                    #             stringFeed = " F{}".format(int(segmentFeed))
                                                
                    #         outputFile.write(
                    #             get_extrusion_command(
                    #                 currentPosition.x,
                    #                 currentPosition.y,
                    #                 segmentLengthRatio * extrusionLength * max_flow / 100,
                    #             ) + stringFeed + '\n'
                    #         )
                    #     else:
                    #         outPutLine = ""
                    #         for element in splitLine:
                    #             if "E" in element:
                    #                 outPutLine = outPutLine + "E" + str(round(extrusionLength * max_flow / 100, 5))
                    #             else:
                    #                 outPutLine = outPutLine + element + " "
                    #         outPutLine = outPutLine + "\n"
                    #         outputFile.write(outPutLine)
                    #     writtenToFile = 1

                    # gyroid or honeycomb
                    if infill_type == InfillType.SMALL_SEGMENTS:
                        # target_points = []
                        # for target in infill_targets:
                        #     if target[2] <= current_layer_number * layer_height < target[2] + target[3]:
                        #         target_points
                        # shortestDistance = min_distance_from_target_points(
                        #     Segment(lastPosition, currentPosition), target_points
                        # )

                        outPutLine = ""
                        for element in splitLine:
                            if "E" in element:
                                newE = float(element[1:]) * min_flow / 100
                                segmentFeed = current_feed / (min_flow / 100)
                                for target in effective_infill_targets:
                                    dist = min_distance_from_target_points(Segment(lastPosition, currentPosition), [Point2D(target[0], target[1])])
                                    # print('yes', dist, target[4])
                                    if dist < target[4]:
                                        if enable_gradient:
                                            tmpE = float(element[1:]) * mapRange(
                                                (0, target[4]), (max_flow / 100, min_flow / 100), dist
                                            )
                                            tmpSegmentFeed = current_feed / mapRange((0, target[4]), (max_flow / 100, min_flow / 100), dist)
                                        else:
                                            tmpE = float(element[1:]) * max_flow / 100
                                            tmpSegmentFeed = current_feed / (max_flow / 100)
                                        if tmpE > newE:
                                            newE = tmpE
                                            segmentFeed = tmpSegmentFeed
                                if gradual_speed:
                                    if segmentFeed > (current_feed * max_over_speed_factor/100):
                                        segmentFeed = current_feed * max_over_speed_factor/100
                                    if segmentFeed < (current_feed * min_over_speed_factor/100):
                                        segmentFeed = current_feed * min_over_speed_factor/100
                                    stringFeed = " F{}".format(int(segmentFeed))

                                outPutLine = outPutLine + "E" + str(round(newE, 5))
                                if not " F" in outPutLine and gradual_speed:
                                    outPutLine = outPutLine + stringFeed
                            else:
                                outPutLine = outPutLine + element + " "
                        outPutLine = outPutLine + "\n"
                        outputFile.write(outPutLine)
                        writtenToFile = 1
                if ";" in currentLine:
                    currentSection = Section.NOTHING

            # line with move
            if " X" in currentLine and " Y" in currentLine and ("G1" in currentLine or "G0" in currentLine):
                lastPosition = getXY(currentLine)

            # write uneditedLine
            if writtenToFile == 0:
                outputFile.write(currentLine)

