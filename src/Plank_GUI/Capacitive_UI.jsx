// This file is meant to be used to visualize the historical data from the capacitive
// sensors of the plank. The data is read from a CSV file and displayed in a heatmap
// format. The heatmap is a 4x4 grid of squares, each representing a capacitive sensor.
// The color of each square is determined by the value of the sensor reading, with
// higher values being represented by a darker shade of blue.

import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import Papa from "papaparse";

const CapacitiveSensorHeatmap = () => {
  const [data, setData] = useState([]);
  const [selectedTime, setSelectedTime] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await window.fs.readFile("CWP_Capa_data.csv", {
          encoding: "utf8",
        });
        const result = Papa.parse(response, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
        });
        setData(result.data);
      } catch (error) {
        console.error("Error loading data:", error);
      }
    };
    loadData();
  }, []);

  const getColor = (value, maxValue) => {
    const intensity = Math.min((value / maxValue) * 255, 255);
    return `rgb(0, 0, ${Math.round(intensity)})`;
  };

  const getMaxValue = (sensorIndex) => {
    return Math.max(...data.map((row) => row[`capacitive_${sensorIndex}`]));
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const renderHeatmap = () => {
    if (!data.length) return null;

    const gridItems = [];
    const currentData = selectedTime
      ? data.find((d) => d.timestamp === selectedTime)
      : data[data.length - 1];

    for (let i = 0; i < 16; i++) {
      const value = currentData[`capacitive_${i}`];
      const maxValue = getMaxValue(i);

      gridItems.push(
        <div
          key={i}
          className='relative flex flex-col items-center justify-center p-2 border border-gray-200'
        >
          <div
            className='w-full h-16 rounded'
            style={{ backgroundColor: getColor(value, maxValue) }}
          />
          <div className='mt-1 text-xs text-center'>
            <div>Sensor {i}</div>
            <div className='font-bold'>{value}</div>
          </div>
        </div>
      );
    }

    return <div className='grid grid-cols-4 gap-2 p-4'>{gridItems}</div>;
  };

  return (
    <Card className='w-full max-w-4xl'>
      <CardHeader>
        <CardTitle>Capacitive Sensor Readings</CardTitle>
        <div className='text-sm text-gray-500'>
          {selectedTime ? formatTimestamp(selectedTime) : "Latest Reading"}
        </div>
      </CardHeader>
      <CardContent>
        <div className='mb-4'>
          <div className='text-sm mb-2'>Time Slider:</div>
          <input
            type='range'
            min='0'
            max={data.length - 1}
            className='w-full'
            onChange={(e) => {
              const index = parseInt(e.target.value);
              setSelectedTime(data[index]?.timestamp);
            }}
          />
        </div>
        {renderHeatmap()}
        <div className='mt-4 flex justify-between text-sm text-gray-500'>
          <div>Low</div>
          <div className='flex items-center'>
            <div className='w-20 h-4 bg-gradient-to-r from-black to-blue-600'></div>
          </div>
          <div>High</div>
        </div>
      </CardContent>
    </Card>
  );
};

export default CapacitiveSensorHeatmap;
